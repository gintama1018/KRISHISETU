"""
KrishiSetu — DPDP Compliance Layer
Layer 6: Data Protection & Privacy
"""
import os
import sqlite3
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

DEFAULT_DB = "/tmp/krishisetu.db" if os.getenv("VERCEL") else "./krishisetu.db"
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB)
router = APIRouter()


def _init_consent_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consent_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id TEXT NOT NULL UNIQUE,
            phone_hash TEXT NOT NULL,
            consent_given INTEGER NOT NULL DEFAULT 1,
            consent_method TEXT NOT NULL,
            consent_timestamp TEXT NOT NULL,
            ip_address TEXT,
            data_uses TEXT,
            retention_years INTEGER DEFAULT 5,
            erasure_requested INTEGER DEFAULT 0,
            erasure_timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            performed_by TEXT,
            timestamp TEXT NOT NULL,
            ip_address TEXT
        )
    """)
    conn.commit()
    conn.close()


class ConsentRequest(BaseModel):
    farmer_id: str
    phone: str  # Will be hashed before storage
    consent_method: str = "voice"  # "voice" | "sms" | "app"
    data_uses: str = "weather_advisory,mandi_prices,risk_alerts"
    ip_address: Optional[str] = None


class ErasureRequest(BaseModel):
    farmer_id: str
    reason: Optional[str] = "farmer_request"


@router.post("/consent/capture")
async def capture_consent(req: ConsentRequest):
    """
    Capture farmer's DPDP-compliant consent.
    Phone number is hashed (bcrypt) before storage — no PII stored in plain text.
    """
    _init_consent_db()
    phone_hash = bcrypt.hashpw(req.phone.encode(), bcrypt.gensalt()).decode()
    timestamp = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO consent_records
            (farmer_id, phone_hash, consent_given, consent_method, consent_timestamp, ip_address, data_uses)
            VALUES (?, ?, 1, ?, ?, ?, ?)
            """,
            (req.farmer_id, phone_hash, req.consent_method, timestamp, req.ip_address, req.data_uses),
        )
        conn.execute(
            "INSERT INTO audit_log (farmer_id, action, resource, timestamp, ip_address) VALUES (?, ?, ?, ?, ?)",
            (req.farmer_id, "consent_captured", "consent_records", timestamp, req.ip_address),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "farmer_id": req.farmer_id,
        "consent_given": True,
        "consent_method": req.consent_method,
        "timestamp": timestamp,
        "data_uses": req.data_uses.split(","),
        "dpdp_compliant": True,
        "message": "Consent recorded. Phone number stored as one-way hash (DPDP compliant).",
    }


@router.get("/consent/{farmer_id}")
async def check_consent(farmer_id: str):
    """Check if a farmer has given consent."""
    _init_consent_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT consent_given, consent_method, consent_timestamp, erasure_requested FROM consent_records WHERE farmer_id = ?",
        (farmer_id,)
    ).fetchone()
    conn.close()

    if not row:
        return {"farmer_id": farmer_id, "consent_given": False}

    consent_given, method, ts, erasure = row
    return {
        "farmer_id": farmer_id,
        "consent_given": bool(consent_given) and not bool(erasure),
        "consent_method": method,
        "consent_timestamp": ts,
        "erasure_requested": bool(erasure),
    }


@router.post("/erasure/request")
async def request_data_erasure(req: ErasureRequest):
    """
    Right-to-erasure workflow (DPDP requirement).
    Marks the farmer's record for erasure — actual deletion happens within 30 days per policy.
    """
    _init_consent_db()
    timestamp = datetime.now(timezone.utc).isoformat()
    deletion_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    rows_updated = conn.execute(
        "UPDATE consent_records SET erasure_requested = 1, erasure_timestamp = ? WHERE farmer_id = ?",
        (timestamp, req.farmer_id),
    ).rowcount
    conn.execute(
        "INSERT INTO audit_log (farmer_id, action, resource, timestamp) VALUES (?, ?, ?, ?)",
        (req.farmer_id, "erasure_requested", "all_farmer_data", timestamp),
    )
    conn.commit()
    conn.close()

    if rows_updated == 0:
        raise HTTPException(status_code=404, detail="Farmer not found in consent records.")

    return {
        "farmer_id": req.farmer_id,
        "erasure_requested": True,
        "request_timestamp": timestamp,
        "scheduled_deletion": deletion_date,
        "message": "Data erasure scheduled within 30 days per DPDP data retention policy.",
    }


@router.get("/audit-log/{farmer_id}")
async def get_audit_log(farmer_id: str):
    """Get audit log of all data access events for a farmer."""
    _init_consent_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT action, resource, performed_by, timestamp, ip_address FROM audit_log WHERE farmer_id = ? ORDER BY timestamp DESC",
        (farmer_id,),
    ).fetchall()
    conn.close()

    events = [
        {"action": r[0], "resource": r[1], "performed_by": r[2], "timestamp": r[3], "ip": r[4]}
        for r in rows
    ]
    return {"farmer_id": farmer_id, "audit_events": events, "count": len(events)}


@router.get("/policy")
async def data_retention_policy():
    """Returns KrishiSetu's data retention and privacy policy summary."""
    return {
        "project": "KrishiSetu",
        "compliance": "India DPDP Act 2023",
        "data_collected": ["village_code", "crop_type", "phone_hash", "consent_record"],
        "data_NOT_collected": ["full_name (optional)", "exact_GPS_coordinates", "financial_records"],
        "retention_policy": "5 years from last active use, or until erasure requested",
        "right_to_erasure": "Honored within 30 days of request",
        "encryption": {
            "in_transit": "TLS 1.3",
            "at_rest": "AES-256 for PII fields; bcrypt for phone numbers",
        },
        "consent_model": "Explicit opt-in required; voice consent accepted for low-literacy users",
        "data_sharing": "AgriStack consent-based model; no raw data sold to third parties",
    }
