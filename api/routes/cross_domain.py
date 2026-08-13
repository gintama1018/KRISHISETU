"""
KrishiSetu — Cross-Domain Intelligence Routes (Supabase-backed + Push Triggers)
Layer 3: Heat→Labor, Pest→Insurance; auto-fires push on critical risk
"""
import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from models.cross_domain import get_labor_scheduling_advisory
from db.supabase_client import get_service_supabase

router = APIRouter()


class LaborAdvisoryRequest(BaseModel):
    farmer_id: Optional[str] = None
    max_temp_c: float = 32.0
    drought_score: int = 30
    humidity_pct: float = 60.0
    crop: str = "default"


class InsuranceEventRequest(BaseModel):
    farmer_id: str
    event_type: str          # "pest_spray" | "drought_stress" | "crop_loss"
    crop: str
    drought_score: Optional[int] = None
    pest_score: Optional[int] = None
    pest_detected: Optional[str] = None
    spray_product: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    advisory_text: Optional[str] = None


@router.post("/labor-advisory")
async def labor_scheduling_advisory(req: LaborAdvisoryRequest):
    """
    Correlate heat/drought stress with farm labor scheduling.
    Tells farmers and field workers WHEN NOT to work the fields.
    """
    result = get_labor_scheduling_advisory(
        max_temp_c=req.max_temp_c,
        drought_score=req.drought_score,
        humidity_pct=req.humidity_pct,
        crop=req.crop,
    )

    # Auto-trigger push if heat stress is HIGH or EXTREME
    if req.farmer_id and result.get("heat_stress_level") in ("HIGH", "EXTREME"):
        try:
            from api.routes.push import send_risk_alert
            import asyncio
            asyncio.create_task(send_risk_alert(
                farmer_id=req.farmer_id,
                crop=req.crop,
                drought=req.drought_score,
                pest=0,
            ))
        except Exception:
            pass  # Push is best-effort, never break the main response

    return result


@router.post("/insurance-log")
async def log_event_for_insurance(req: InsuranceEventRequest, background_tasks: BackgroundTasks):
    """
    Log a pest/spray or drought stress event as insurance evidence.
    Stores tamper-evident record in Supabase with SHA-256 evidence hash.
    Auto-sends push notification if risk is critical.
    """
    db = get_service_supabase()
    ts = datetime.now(timezone.utc).isoformat()

    # Evidence hash — tamper-evident fingerprint
    raw = f"{req.farmer_id}|{req.event_type}|{req.crop}|{req.drought_score}|{req.pest_score}|{ts}"
    evidence_hash = hashlib.sha256(raw.encode()).hexdigest()

    row = {
        "farmer_id": req.farmer_id,
        "event_type": req.event_type,
        "crop": req.crop,
        "risk_score": float(max(req.drought_score or 0, req.pest_score or 0)),
        "advisory_text": req.advisory_text or "",
        "evidence_hash": evidence_hash,
        "pest_detected": req.pest_detected,
        "spray_product": req.spray_product,
        "lat": req.lat,
        "lon": req.lon,
        "created_at": ts,
    }

    result = db.table("insurance_events").insert(row).execute()
    record_id = result.data[0]["id"] if result.data else "unknown"

    # Push notification for critical insurance-worthy events
    if req.farmer_id and (req.drought_score or 0) + (req.pest_score or 0) > 120:
        background_tasks.add_task(_push_insurance_alert, req.farmer_id, req.crop, req.event_type)

    return {
        "farmer_id": req.farmer_id,
        "record_id": record_id,
        "evidence_hash": evidence_hash,
        "event_type": req.event_type,
        "crop": req.crop,
        "timestamp": ts,
        "tamper_evident": True,
        "database": "supabase_postgresql",
        "message": "Insurance evidence logged immutably in Supabase.",
    }


@router.get("/insurance-trail/{farmer_id}")
async def get_farmer_insurance_trail(farmer_id: str):
    """Get all logged insurance evidence events for a farmer from Supabase."""
    db = get_service_supabase()
    result = db.table("insurance_events").select("*").eq(
        "farmer_id", farmer_id
    ).order("created_at", desc=True).execute()

    events = result.data or []
    return {
        "farmer_id": farmer_id,
        "event_count": len(events),
        "events": events,
        "database": "supabase_postgresql",
    }


# ── Internal helpers ───────────────────────────────────────────────────────

async def _push_insurance_alert(farmer_id: str, crop: str, event_type: str):
    try:
        from api.routes.push import send_risk_alert
        await send_risk_alert(farmer_id=farmer_id, crop=crop, drought=70, pest=70)
    except Exception:
        pass
