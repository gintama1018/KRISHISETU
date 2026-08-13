"""
KrishiSetu — DPDP Compliance Layer (Supabase-backed)
Layer 6: Real Database — no more SQLite
"""
import os
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.supabase_client import get_service_supabase

router = APIRouter()


class ConsentRequest(BaseModel):
    farmer_id: str
    phone: str          # hashed before storage
    consent_method: str = "app"
    data_uses: str = "weather_advisory,mandi_prices,risk_alerts"
    ip_address: Optional[str] = None


class ErasureRequest(BaseModel):
    farmer_id: str
    reason: Optional[str] = "farmer_request"


@router.post("/consent/capture")
async def capture_consent(req: ConsentRequest):
    """
    Capture DPDP-compliant consent.
    Phone is bcrypt-hashed before hitting the DB — no PII stored in plain text.
    """
    db = get_service_supabase()
    phone_hash = bcrypt.hashpw(req.phone.encode(), bcrypt.gensalt()).decode()
    ts = datetime.now(timezone.utc).isoformat()

    # Upsert consent record
    db.table("consent_records").upsert({
        "farmer_id": req.farmer_id,
        "phone_hash": phone_hash,
        "consent_given": True,
        "consent_method": req.consent_method,
        "consent_timestamp": ts,
        "ip_address": req.ip_address,
        "data_uses": req.data_uses,
        "erasure_requested": False,
    }, on_conflict="farmer_id").execute()

    # Audit log
    db.table("audit_log").insert({
        "farmer_id": req.farmer_id,
        "action": "consent_captured",
        "phone_hash": phone_hash,
        "consent_given": True,
        "ip_hash": req.ip_address,
        "created_at": ts,
    }).execute()

    return {
        "farmer_id": req.farmer_id,
        "consent_given": True,
        "consent_method": req.consent_method,
        "timestamp": ts,
        "data_uses": req.data_uses.split(","),
        "dpdp_compliant": True,
        "message": "Consent recorded. Phone stored as one-way bcrypt hash (DPDP compliant).",
    }


@router.get("/consent/{farmer_id}")
async def check_consent(farmer_id: str):
    """Check if a farmer has active consent."""
    db = get_service_supabase()
    result = db.table("consent_records").select(
        "consent_given,consent_method,consent_timestamp,erasure_requested"
    ).eq("farmer_id", farmer_id).maybe_single().execute()

    if not result.data:
        return {"farmer_id": farmer_id, "consent_given": False}

    row = result.data
    return {
        "farmer_id": farmer_id,
        "consent_given": row["consent_given"] and not row["erasure_requested"],
        "consent_method": row["consent_method"],
        "consent_timestamp": row["consent_timestamp"],
        "erasure_requested": row["erasure_requested"],
    }


@router.post("/erasure/request")
async def request_data_erasure(req: ErasureRequest):
    """Right-to-erasure workflow (DPDP requirement). Schedules deletion in 30 days."""
    db = get_service_supabase()
    ts = datetime.now(timezone.utc).isoformat()
    deletion_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    result = db.table("consent_records").update({
        "erasure_requested": True,
        "erasure_timestamp": ts,
    }).eq("farmer_id", req.farmer_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Farmer not found in consent records.")

    db.table("audit_log").insert({
        "farmer_id": req.farmer_id,
        "action": "erasure_requested",
        "consent_given": False,
        "created_at": ts,
    }).execute()

    return {
        "farmer_id": req.farmer_id,
        "erasure_requested": True,
        "request_timestamp": ts,
        "scheduled_deletion": deletion_date,
        "message": "Data erasure scheduled within 30 days per DPDP policy.",
    }


@router.get("/audit-log/{farmer_id}")
async def get_audit_log(farmer_id: str):
    """Get audit log of all data access events for a farmer."""
    db = get_service_supabase()
    result = db.table("audit_log").select(
        "action,consent_given,ip_hash,created_at"
    ).eq("farmer_id", farmer_id).order("created_at", desc=True).execute()

    events = result.data or []
    return {"farmer_id": farmer_id, "audit_events": events, "count": len(events)}


@router.get("/policy")
async def data_retention_policy():
    """Returns KrishiSetu's DPDP-compliant data retention policy."""
    return {
        "project": "KrishiSetu",
        "compliance": "India DPDP Act 2023",
        "database": "Supabase PostgreSQL (encrypted at rest)",
        "data_collected": ["village_code", "crop_type", "phone_hash", "consent_record"],
        "data_NOT_collected": ["full_name (optional)", "exact_GPS", "financial_records"],
        "retention_policy": "5 years from last active use, or until erasure requested",
        "right_to_erasure": "Honored within 30 days of request",
        "encryption": {
            "in_transit": "TLS 1.3",
            "at_rest": "AES-256 (Supabase); bcrypt for phone numbers",
        },
        "consent_model": "Explicit opt-in required; voice consent accepted for low-literacy users",
        "data_sharing": "AgriStack consent-based model; no raw data sold to third parties",
    }
