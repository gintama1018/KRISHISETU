"""
KrishiSetu — AgriStack Mock Sandbox Server
Serves as a local mock of the AgriStack farmer registry API.
In Final Round: swap AGRISTACK_SANDBOX_URL to the live AgriStack sandbox URL.
"""
import uuid
import sqlite3
import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

DB_PATH = os.getenv("DATABASE_PATH", "./krishisetu.db")
router = APIRouter()


def _init_mock_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_farmers (
            farmer_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            village_code TEXT,
            district TEXT,
            state TEXT,
            crop TEXT,
            plot_area_acres REAL,
            language_preference TEXT,
            consent_given INTEGER,
            registered_at TEXT
        )
    """)
    conn.commit()
    # Seed with demo farmers for the hackathon demo
    demo_farmers = [
        ("F001", "Ramesh Kalita", "+917012345678", "ASM-KAM-001", "Kamrup", "Assam", "rice", 2.5, "Assamese", 1),
        ("F002", "Priya Devi", "+919876543210", "ASM-KAM-001", "Kamrup", "Assam", "mustard", 1.2, "Assamese", 1),
        ("F003", "Bikash Borah", "+918765432109", "ASM-KAM-002", "Kamrup Metropolitan", "Assam", "maize", 3.0, "Hindi", 1),
        ("F004", "Mira Begum", "+916543210987", "ASM-NAL-001", "Nalbari", "Assam", "wheat", 1.8, "Assamese", 1),
        ("F005", "Gopal Singh", "+915432109876", "ASM-NAL-001", "Nalbari", "Assam", "rice", 4.5, "Hindi", 1),
    ]
    for f in demo_farmers:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO mock_farmers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (*f, "2026-01-01T00:00:00Z"),
            )
        except Exception:
            pass
    conn.commit()
    conn.close()


class MockFarmerRegistration(BaseModel):
    name: str
    phone: str
    village_code: str
    district: str
    state: str
    crop: str
    plot_area_acres: float
    language_preference: str = "Hindi"
    consent_given: bool = False


@router.post("/farmers/register")
async def mock_register_farmer(req: MockFarmerRegistration):
    _init_mock_db()
    if not req.consent_given:
        raise HTTPException(status_code=400, detail="Consent required.")

    farmer_id = f"F{uuid.uuid4().hex[:6].upper()}"
    ts = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO mock_farmers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (farmer_id, req.name, req.phone, req.village_code, req.district,
         req.state, req.crop, req.plot_area_acres, req.language_preference,
         1, ts),
    )
    conn.commit()
    conn.close()

    return {
        "farmer_id": farmer_id,
        "agristack_id": f"AGS-{farmer_id}",
        "name": req.name,
        "village_code": req.village_code,
        "registered_at": ts,
        "source": "AgriStack Mock Sandbox",
    }


@router.get("/farmers/{farmer_id}")
async def mock_get_farmer(farmer_id: str):
    _init_mock_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT * FROM mock_farmers WHERE farmer_id = ?", (farmer_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Farmer {farmer_id} not found.")

    cols = ["farmer_id", "name", "phone", "village_code", "district", "state",
             "crop", "plot_area_acres", "language_preference", "consent_given", "registered_at"]
    return {**dict(zip(cols, row)), "source": "AgriStack Mock Sandbox"}


@router.get("/farmers")
async def mock_get_farmers_by_village(village_code: str = Query(...)):
    _init_mock_db()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT * FROM mock_farmers WHERE village_code = ?", (village_code,)
    ).fetchall()
    conn.close()

    cols = ["farmer_id", "name", "phone", "village_code", "district", "state",
             "crop", "plot_area_acres", "language_preference", "consent_given", "registered_at"]
    return {
        "village_code": village_code,
        "count": len(rows),
        "farmers": [dict(zip(cols, r)) for r in rows],
        "source": "AgriStack Mock Sandbox",
    }
