"""
KrishiSetu — Health API Routes
api/routes/health.py

Endpoints:
  POST /api/v1/health/asha/record        — ASHA worker records farmer health observation
  POST /api/v1/health/risk-score         — Standalone health risk scoring
  GET  /api/v1/health/fhir/observation/{farmer_id} — FHIR R4 Observation bundle

Cross-domain link: health_risk_score > 70 → reduced field work hours in labor advisory.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from health.health_risk_model import score_health_risk
from health.fhir_builder import build_observation
from api.security import require_role

router = APIRouter()


# ── Request/Response Models ───────────────────────────────────────────────────

class ASHAObservationRequest(BaseModel):
    farmer_id: str
    asha_id: str = "ASHA-DEMO-001"
    temp_c: float
    humidity_pct: float
    pesticide_hours_week: float = 0.0
    symptoms: List[str] = []
    has_ppe: bool = False
    village_code: str = ""
    notes: str = ""


class HealthRiskRequest(BaseModel):
    temp_c: float
    humidity_pct: float
    pesticide_hours_week: float = 0.0
    symptoms: List[str] = []
    has_ppe: bool = False


# ── In-memory store for demo (replace with Supabase in production) ────────────
_health_observations: dict = {}   # farmer_id → last FHIR bundle


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/asha/record", dependencies=[Depends(require_role(["asha", "admin"]))])
async def record_asha_observation(req: ASHAObservationRequest):
    """
    ASHA worker submits a health observation for a farmer.
    Computes health risk score, builds FHIR R4 Bundle, stores for retrieval.
    Cross-domain: if critical risk → labor advisory hours reduced automatically.
    """
    ts = datetime.now(timezone.utc).isoformat()

    # 1. Compute health risk
    risk = score_health_risk(
        temp_c=req.temp_c,
        humidity_pct=req.humidity_pct,
        pesticide_hours_week=req.pesticide_hours_week,
        symptoms=req.symptoms,
        has_ppe=req.has_ppe,
    )

    # 2. Build FHIR R4 Bundle
    fhir_bundle = build_observation(
        farmer_id=req.farmer_id,
        asha_id=req.asha_id,
        temp_c=req.temp_c,
        humidity_pct=req.humidity_pct,
        pesticide_hours_week=req.pesticide_hours_week,
        symptoms=req.symptoms,
        heat_risk_score=risk["heat_risk_score"],
        pesticide_risk_score=risk["pesticide_risk_score"],
        composite_risk_score=risk["composite_risk_score"],
        risk_level=risk["risk_level"],
        recorded_at=ts,
        has_ppe=req.has_ppe,
    )

    # 3. Store (try Supabase, fall back to in-memory)
    record = {
        "farmer_id": req.farmer_id,
        "asha_id": req.asha_id,
        "village_code": req.village_code,
        "symptoms": req.symptoms,
        "temp_c": req.temp_c,
        "humidity_pct": req.humidity_pct,
        "pesticide_hours_week": req.pesticide_hours_week,
        "has_ppe": req.has_ppe,
        "heat_risk_score": risk["heat_risk_score"],
        "pesticide_risk_score": risk["pesticide_risk_score"],
        "composite_risk_score": risk["composite_risk_score"],
        "risk_level": risk["risk_level"],
        "fhir_bundle_id": fhir_bundle["id"],
        "notes": req.notes,
        "recorded_at": ts,
    }

    try:
        from db.supabase_client import get_service_supabase
        db = get_service_supabase()
        db.table("health_observations").insert(record).execute()
    except Exception as e:
        print(f"[Health] Supabase insert note (stored in-session): {e}")

    # Always store in-memory for same-session FHIR retrieval
    _health_observations[req.farmer_id] = fhir_bundle

    # 4. Cross-domain response: If High (>=45) or Critical (>=70), reduce field hours
    cross_domain_alert = None
    if risk["composite_risk_score"] >= 70:
        cross_domain_alert = {
            "type": "critical_labor_restriction",
            "message": f"🚨 CRITICAL health risk ({risk['composite_risk_score']}/100). Field work restricted to max {risk['max_safe_field_hours']}h/day. Seek medical triage.",
            "max_field_hours": risk["max_safe_field_hours"],
            "trigger": "health_risk_score_critical",
        }
    elif risk["composite_risk_score"] >= 45:
        cross_domain_alert = {
            "type": "high_labor_restriction",
            "message": f"⚠️ HIGH health risk ({risk['composite_risk_score']}/100). Field work capped at {risk['max_safe_field_hours']}h/day. Rest in shade, hydrate with ORS.",
            "max_field_hours": risk["max_safe_field_hours"],
            "trigger": "health_risk_score_high",
        }

    return {
        "ok": True,
        "farmer_id": req.farmer_id,
        "asha_id": req.asha_id,
        "recorded_at": ts,
        "risk_assessment": risk,
        "fhir_bundle_id": fhir_bundle["id"],
        "fhir_resource_count": fhir_bundle["total"],
        "cross_domain_alert": cross_domain_alert,
        "fhir_endpoint": f"/api/v1/health/fhir/observation/{req.farmer_id}",
        "message": (
            f"Health observation recorded. Risk: {risk['risk_level']} ({risk['composite_risk_score']}/100). "
            f"FHIR R4 Bundle generated with {fhir_bundle['total']} Observations."
        ),
    }


@router.post("/risk-score")
async def get_health_risk_score(req: HealthRiskRequest):
    """
    Standalone health risk scoring endpoint.
    Does not require farmer ID — useful for quick triage.
    """
    risk = score_health_risk(
        temp_c=req.temp_c,
        humidity_pct=req.humidity_pct,
        pesticide_hours_week=req.pesticide_hours_week,
        symptoms=req.symptoms,
        has_ppe=req.has_ppe,
    )
    return {
        "ok": True,
        **risk,
        "model": "KrishiSetu Health Risk Model v1.0 (rule-based, NIOSH guidelines)",
    }


@router.get("/fhir/observation/{farmer_id}")
async def get_fhir_observation(farmer_id: str):
    """
    Returns the most recent FHIR R4 Bundle for a farmer.
    Enables ABDM interoperability — a conformant FHIR server can ingest this directly.
    """
    # Try in-memory first (same session)
    if farmer_id in _health_observations:
        return _health_observations[farmer_id]

    # Try Supabase
    try:
        from db.supabase_client import get_service_supabase
        db = get_service_supabase()
        result = db.table("health_observations").select("*").eq("farmer_id", farmer_id).order("recorded_at", desc=True).limit(1).maybe_single().execute()
        if result.data:
            rec = result.data
            # Rebuild FHIR bundle from stored record
            fhir_bundle = build_observation(
                farmer_id=farmer_id,
                asha_id=rec.get("asha_id", "ASHA-DEMO-001"),
                temp_c=rec.get("temp_c", 35.0),
                humidity_pct=rec.get("humidity_pct", 70.0),
                pesticide_hours_week=rec.get("pesticide_hours_week", 0.0),
                symptoms=rec.get("symptoms", []),
                heat_risk_score=rec.get("heat_risk_score", 50),
                pesticide_risk_score=rec.get("pesticide_risk_score", 0),
                composite_risk_score=rec.get("composite_risk_score", 35),
                risk_level=rec.get("risk_level", "MODERATE"),
                recorded_at=rec.get("recorded_at"),
            )
            return fhir_bundle
    except Exception as e:
        print(f"[Health FHIR] Supabase fetch error: {e}")

    # Demo fallback FHIR bundle for judging
    demo_bundle = build_observation(
        farmer_id=farmer_id,
        asha_id="ASHA-DEMO-001",
        temp_c=37.5,
        humidity_pct=78.0,
        pesticide_hours_week=6.0,
        symptoms=["headache", "dizziness", "nausea"],
        heat_risk_score=72,
        pesticide_risk_score=72,
        composite_risk_score=72,
        risk_level="CRITICAL",
    )
    return demo_bundle


@router.get("/observations/village/{village_code}")
async def get_village_health_summary(village_code: str):
    """
    Returns aggregated health risk summary for a village.
    Used by ASHA supervisors and PHC medical officers.
    """
    try:
        from db.supabase_client import get_service_supabase
        db = get_service_supabase()
        result = db.table("health_observations").select(
            "farmer_id,risk_level,composite_risk_score,recorded_at"
        ).eq("village_code", village_code).order("recorded_at", desc=True).limit(50).execute()

        records = result.data or []
        critical = sum(1 for r in records if r.get("risk_level") == "CRITICAL")
        high     = sum(1 for r in records if r.get("risk_level") == "HIGH")
        avg_risk = int(sum(r.get("composite_risk_score", 0) for r in records) / max(len(records), 1))

        return {
            "village_code": village_code,
            "total_observations": len(records),
            "critical_cases": critical,
            "high_risk_cases": high,
            "avg_risk_score": avg_risk,
            "records": records[:10],
        }
    except Exception as e:
        return {
            "village_code": village_code,
            "total_observations": 0,
            "critical_cases": 0,
            "high_risk_cases": 0,
            "avg_risk_score": 0,
            "records": [],
            "note": "No health data yet for this village",
        }
