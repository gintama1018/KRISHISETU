"""
KrishiSetu — API Routes: Farmer Registry (AgriStack)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ingestion.agristack_adapter import register_farmer, get_farmer_profile, get_farmers_by_village

router = APIRouter()


class FarmerRegistrationRequest(BaseModel):
    name: str
    phone: str
    village_code: str
    district: str
    state: str
    crop: str
    plot_area_acres: float
    language_preference: str = "Hindi"
    # Consent (DPDP requirement)
    consent_given: bool = False
    consent_timestamp: Optional[str] = None


@router.post("/register")
async def register_new_farmer(req: FarmerRegistrationRequest):
    """Register a farmer in AgriStack registry (mock/sandbox)."""
    if not req.consent_given:
        raise HTTPException(status_code=400, detail="Farmer consent is required before registration (DPDP compliance).")
    result = await register_farmer(req.model_dump())
    return result


@router.get("/{farmer_id}")
async def get_farmer(farmer_id: str):
    """Fetch a farmer's profile from AgriStack."""
    return await get_farmer_profile(farmer_id)


@router.get("/village/{village_code}")
async def get_village_farmers(village_code: str):
    """Get all farmers in a village — for agri-officer dashboard."""
    farmers = await get_farmers_by_village(village_code)
    return {"village_code": village_code, "count": len(farmers), "farmers": farmers}
