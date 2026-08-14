"""
KrishiSetu — Farmer Registry (Supabase-backed, real auth)
Layer 1: Real farmer profiles stored in Supabase PostgreSQL
"""
import uuid
import bcrypt
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.supabase_client import get_service_supabase

router = APIRouter()


class FarmerRegistrationRequest(BaseModel):
    farmer_id: Optional[str] = None
    name: str
    phone: str
    village_code: str
    district: str = ""
    state: str
    crop: str
    plot_area_acres: float = 2.0
    language_preference: str = "English"
    consent_given: bool = False
    consent_timestamp: Optional[str] = None


@router.post("/register")
async def register_new_farmer(req: FarmerRegistrationRequest):
    """Register a farmer in Supabase — phone bcrypt-hashed before storage."""
    if not req.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Farmer consent is required before registration (DPDP compliance)."
        )

    db = get_service_supabase()
    phone_hash = bcrypt.hashpw(req.phone.encode(), bcrypt.gensalt()).decode()
    ts = datetime.now(timezone.utc).isoformat()

    row = {
        "name": req.name,
        "phone_hash": phone_hash,
        "crop": req.crop,
        "state": req.state,
        "district": req.district,
        "village_code": req.village_code,
        "area_acres": req.plot_area_acres,
        "language": req.language_preference,
        "consent_given": req.consent_given,
        "consent_timestamp": req.consent_timestamp or ts,
        "created_at": ts,
    }

    # Only include farmer_id if valid UUID format, else omit so Supabase generates UUID
    if req.farmer_id:
        try:
            valid_uuid = str(uuid.UUID(req.farmer_id))
            row["id"] = valid_uuid
        except ValueError:
            pass  # Omit string IDs like 'farmer_123', let Supabase gen_random_uuid() generate it

    result = db.table("farmers").insert(row).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to register farmer in database.")

    farmer = result.data[0]
    farmer_id = farmer["id"]

    # ── AgriStack Sandbox Registration ────────────────────────────────────────
    # Calls the AgriStack-compatible adapter (mock sandbox locally, live sandbox in production).
    # agristack_registered is ONLY true when the adapter call actually succeeds.
    agristack_registered = False
    agristack_farmer_id = None
    try:
        from ingestion.agristack_adapter import register_farmer as agristack_register
        agri_data = {
            "farmer_id": farmer_id,
            "name": req.name,
            "phone": req.phone,
            "village_code": req.village_code,
            "district": req.district,
            "state": req.state,
            "crop": req.crop,
            "plot_area_acres": req.plot_area_acres,
            "language_preference": req.language_preference,
            "consent_given": req.consent_given,
        }
        agri_result = await agristack_register(agri_data)
        agristack_registered = agri_result.get("agristack_verified", False)
        agristack_farmer_id = agri_result.get("farmer_id")
    except Exception as e:
        print(f"[AgriStack] Adapter call failed: {e}")

    return {
        "farmer_id": farmer_id,
        "name": farmer["name"],
        "crop": farmer["crop"],
        "state": farmer["state"],
        "village_code": farmer["village_code"],
        "agristack_registered": agristack_registered,
        "agristack_farmer_id": agristack_farmer_id,
        "dpdp_compliant": True,
        "database": "supabase_postgresql",
        "message": "Farmer registered successfully. Advisory pipeline activated.",
    }


@router.get("/{farmer_id}")
async def get_farmer(farmer_id: str):
    """Fetch a farmer's profile from Supabase."""
    db = get_service_supabase()
    result = db.table("farmers").select(
        "id,name,crop,state,district,village_code,area_acres,language,created_at"
    ).eq("id", farmer_id).maybe_single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")

    return result.data


@router.get("/village/{village_code}")
async def get_village_farmers(village_code: str):
    """Get all farmers in a village — for agri-officer dashboard."""
    db = get_service_supabase()
    result = db.table("farmers").select(
        "id,name,crop,state,area_acres,created_at"
    ).eq("village_code", village_code).execute()

    farmers = result.data or []
    return {
        "village_code": village_code,
        "count": len(farmers),
        "farmers": farmers,
        "database": "supabase_postgresql",
    }
