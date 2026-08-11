"""
KrishiSetu — API Routes: Market Prices (Mandi / AGMARKNET)
"""
from fastapi import APIRouter, Query
from typing import Optional
from ingestion.mandi_feed import get_mandi_prices, get_price_trends

router = APIRouter()


@router.get("/mandi")
async def mandi_prices(
    commodity: str = Query(..., description="Crop/commodity name (e.g. Rice, Wheat, Cotton)"),
    state: Optional[str] = Query(None, description="Filter by state"),
    market: Optional[str] = Query(None, description="Filter by market/mandi name"),
    limit: int = Query(20, description="Max records to return"),
):
    """Get current mandi prices from AGMARKNET."""
    return await get_mandi_prices(commodity, state=state, market=market, limit=limit)


@router.get("/trends")
async def price_trends(
    commodity: str = Query(..., description="Crop/commodity name"),
    state: str = Query("Assam", description="State to query"),
    days: int = Query(30, description="Trend window in days"),
):
    """Get price trend for a commodity (rising / falling / stable)."""
    return await get_price_trends(commodity, state, days)
