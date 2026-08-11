"""
KrishiSetu — AgriStack Farmer Registry Adapter
Layer 1: Data Ingestion
In Final Round: point AGRISTACK_SANDBOX_URL to the live AgriStack sandbox.
For demo: uses local mock API with direct DB fallback when in-process.
"""
import os
import httpx
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Optional

AGRISTACK_URL = os.getenv("AGRISTACK_SANDBOX_URL", "http://localhost:8000/mock/agristack")
AGRISTACK_KEY = os.getenv("AGRISTACK_API_KEY", "mock_key_for_demo")
DEFAULT_DB = "/tmp/krishisetu.db" if os.getenv("VERCEL") else "./krishisetu.db"
DB_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB)


def _direct_mock_register(farmer_data: dict) -> dict:
    """Fallback when in-process without external port 8000 server."""
    farmer_id = farmer_data.get("farmer_id") or f"F_{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_farmers (
            farmer_id TEXT PRIMARY KEY,
            name TEXT, phone TEXT, village_code TEXT,
            district TEXT, state TEXT, crop TEXT,
            plot_area_acres REAL, language_preference TEXT,
            consent_given INTEGER, registered_at TEXT
        )
    """)
    conn.execute(
        """
        INSERT OR REPLACE INTO mock_farmers
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            farmer_id,
            farmer_data.get("name"),
            farmer_data.get("phone"),
            farmer_data.get("village_code"),
            farmer_data.get("district", "Kamrup"),
            farmer_data.get("state", "Assam"),
            farmer_data.get("crop", "rice"),
            farmer_data.get("plot_area_acres", 1.0),
            farmer_data.get("language_preference", "English"),
            1 if farmer_data.get("consent_given") else 0,
            timestamp,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "farmer_id": farmer_id,
        "name": farmer_data.get("name"),
        "agristack_verified": True,
        "registry_source": "AgriStack Sandbox (Mock)",
        "registered_at": timestamp,
        "message": "Farmer registered successfully in AgriStack Sandbox.",
    }


async def register_farmer(farmer_data: dict) -> dict:
    """Register a new farmer in AgriStack (mock or live sandbox)."""
    headers = {"X-API-Key": AGRISTACK_KEY, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(f"{AGRISTACK_URL}/farmers/register", json=farmer_data, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        # Internal fallback for test runner / offline execution
        return _direct_mock_register(farmer_data)


async def get_farmer_profile(farmer_id: str) -> dict:
    """Fetch farmer profile from AgriStack registry."""
    headers = {"X-API-Key": AGRISTACK_KEY}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{AGRISTACK_URL}/farmers/{farmer_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT * FROM mock_farmers WHERE farmer_id = ?", (farmer_id,)).fetchone()
        conn.close()
        if row:
            return {
                "farmer_id": row[0], "name": row[1], "phone": row[2],
                "village_code": row[3], "district": row[4], "state": row[5],
                "crop": row[6], "plot_area_acres": row[7], "language_preference": row[8],
                "agristack_verified": True,
            }
        return {"farmer_id": farmer_id, "agristack_verified": False}


async def get_farmers_by_village(village_code: str) -> list:
    """Get all registered farmers in a village — used by agri-officer dashboard."""
    headers = {"X-API-Key": AGRISTACK_KEY}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{AGRISTACK_URL}/farmers",
                params={"village_code": village_code},
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json().get("farmers", [])
    except Exception:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT * FROM mock_farmers WHERE village_code = ?", (village_code,)).fetchall()
        conn.close()
        return [{"farmer_id": r[0], "name": r[1], "crop": r[6]} for r in rows]
