"""
KrishiSetu — AgriStack Farmer Registry Adapter
Layer 1: Data Ingestion (NEW addition)
In Final Round: point AGRISTACK_SANDBOX_URL to the live AgriStack sandbox.
For demo: uses the local mock server at /mock/agristack/*
"""
import os
import httpx
from typing import Optional

AGRISTACK_URL = os.getenv("AGRISTACK_SANDBOX_URL", "http://localhost:8000/mock/agristack")
AGRISTACK_KEY = os.getenv("AGRISTACK_API_KEY", "mock_key_for_demo")


async def register_farmer(farmer_data: dict) -> dict:
    """Register a new farmer in AgriStack (mock or live sandbox)."""
    headers = {"X-API-Key": AGRISTACK_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{AGRISTACK_URL}/farmers/register", json=farmer_data, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def get_farmer_profile(farmer_id: str) -> dict:
    """Fetch farmer profile from AgriStack registry."""
    headers = {"X-API-Key": AGRISTACK_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{AGRISTACK_URL}/farmers/{farmer_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def get_farmers_by_village(village_code: str) -> list:
    """Get all registered farmers in a village — used by agri-officer dashboard."""
    headers = {"X-API-Key": AGRISTACK_KEY}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{AGRISTACK_URL}/farmers",
            params={"village_code": village_code},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json().get("farmers", [])
