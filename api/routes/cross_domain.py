"""
KrishiSetu — API Routes: Cross-Domain Intelligence
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from models.cross_domain import get_labor_scheduling_advisory, log_insurance_event, get_insurance_trail

router = APIRouter()


class LaborAdvisoryRequest(BaseModel):
    farmer_id: Optional[str] = None
    max_temp_c: float = 32.0
    drought_score: int = 30
    humidity_pct: float = 60.0
    crop: str = "default"


class InsuranceEventRequest(BaseModel):
    farmer_id: str
    event_type: str  # "pest_spray" | "drought_stress" | "crop_loss"
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
    return get_labor_scheduling_advisory(
        max_temp_c=req.max_temp_c,
        drought_score=req.drought_score,
        humidity_pct=req.humidity_pct,
        crop=req.crop,
    )


@router.post("/insurance-log")
async def log_event_for_insurance(req: InsuranceEventRequest):
    """
    Log a pest/spray or drought stress event as insurance evidence.
    Creates an immutable audit trail for future crop-insurance claims.
    """
    return log_insurance_event(
        farmer_id=req.farmer_id,
        event_type=req.event_type,
        crop=req.crop,
        drought_score=req.drought_score,
        pest_score=req.pest_score,
        pest_detected=req.pest_detected,
        spray_product=req.spray_product,
        lat=req.lat,
        lon=req.lon,
        advisory_text=req.advisory_text,
    )


@router.get("/insurance-trail/{farmer_id}")
async def get_farmer_insurance_trail(farmer_id: str):
    """Get all logged insurance evidence events for a farmer."""
    events = get_insurance_trail(farmer_id)
    return {"farmer_id": farmer_id, "event_count": len(events), "events": events}
