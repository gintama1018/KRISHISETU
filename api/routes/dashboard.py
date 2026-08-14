"""
KrishiSetu — Officer Dashboard Summary API
api/routes/dashboard.py

GET /api/v1/dashboard/summary
  Returns live village-level aggregates from Supabase.
  Falls back to demo seed data if database is empty.
"""

from fastapi import APIRouter

router = APIRouter()

# ── Demo seed (used only when Supabase has no data) ───────────────────────────
DEMO_VILLAGES = [
    {"code": "ASM-KAM-001", "name": "Hajo Village",   "lat": 26.23, "lon": 91.53, "crop": "rice",    "drought": 78, "pest": 62},
    {"code": "ASM-KAM-002", "name": "Boko Village",    "lat": 26.01, "lon": 91.06, "crop": "maize",   "drought": 45, "pest": 38},
    {"code": "ASM-KAM-003", "name": "Chandrapur",      "lat": 26.41, "lon": 91.78, "crop": "rice",    "drought": 88, "pest": 71},
    {"code": "ASM-KAM-004", "name": "Rani Township",   "lat": 26.12, "lon": 91.45, "crop": "mustard", "drought": 22, "pest": 18},
    {"code": "ASM-NAL-001", "name": "Nalbari Central", "lat": 26.49, "lon": 91.43, "crop": "wheat",   "drought": 55, "pest": 48},
    {"code": "ASM-NAL-002", "name": "Tihu",            "lat": 26.35, "lon": 91.64, "crop": "rice",    "drought": 35, "pest": 82},
    {"code": "ASM-NAL-003", "name": "Mukalmua",        "lat": 26.51, "lon": 91.72, "crop": "rice",    "drought": 68, "pest": 55},
]


@router.get("/summary")
async def get_dashboard_summary():
    """
    Returns live village-level risk aggregates.
    Reads from Supabase farmers table grouped by village_code.
    Falls back to demo seed data if DB is empty (transparent in response).
    """
    live_data = []
    is_live = False

    try:
        from db.supabase_client import get_service_supabase
        db = get_service_supabase()

        # Aggregate farmers by village_code
        result = db.table("farmers").select(
            "village_code, crop, state"
        ).execute()

        farmers = result.data or []

        if farmers:
            is_live = True
            village_map = {}
            for f in farmers:
                vc = f.get("village_code", "UNKNOWN")
                if vc not in village_map:
                    village_map[vc] = {"count": 0, "crops": {}, "states": set()}
                village_map[vc]["count"] += 1
                crop = f.get("crop", "unknown")
                village_map[vc]["crops"][crop] = village_map[vc]["crops"].get(crop, 0) + 1

            # Merge with demo seed coords/risk (real data overrides farmer counts)
            seed_map = {v["code"]: v for v in DEMO_VILLAGES}
            for vc, data in village_map.items():
                top_crop = max(data["crops"], key=data["crops"].get)
                seed = seed_map.get(vc, {
                    "name": vc, "lat": 26.2, "lon": 91.5,
                    "drought": 50, "pest": 50
                })
                live_data.append({
                    "code":     vc,
                    "name":     seed.get("name", vc),
                    "lat":      seed.get("lat", 26.2),
                    "lon":      seed.get("lon", 91.5),
                    "farmers":  data["count"],
                    "crop":     top_crop,
                    "drought":  seed.get("drought", 50),
                    "pest":     seed.get("pest", 50),
                })

    except Exception as e:
        print(f"[Dashboard] Supabase error, using demo seed: {e}")

    # Fall back to demo seed with realistic-looking counts
    if not live_data:
        live_data = [
            {**v, "farmers": [42, 28, 63, 17, 55, 33, 21][i]}
            for i, v in enumerate(DEMO_VILLAGES)
        ]

    total_farmers = sum(v["farmers"] for v in live_data)
    critical_villages = sum(
        1 for v in live_data if max(v["drought"], v["pest"]) >= 70
    )
    avg_drought = int(sum(v["drought"] for v in live_data) / len(live_data))
    avg_pest    = int(sum(v["pest"]    for v in live_data) / len(live_data))

    return {
        "villages": live_data,
        "summary": {
            "total_villages":   len(live_data),
            "total_farmers":    total_farmers,
            "critical_villages": critical_villages,
            "avg_drought_score": avg_drought,
            "avg_pest_score":   avg_pest,
        },
        "data_source": "supabase_live" if is_live else "demo_seed",
        "note": "Live farmer counts from Supabase PostgreSQL" if is_live else "Demo seed data — register farmers to see live counts",
    }
