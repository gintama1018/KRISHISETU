"""
KrishiSetu — API Routes: Data Ingestion
"""
from fastapi import APIRouter, Query
from ingestion.weather import get_combined_weather_data

router = APIRouter()


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Fetch combined historical (NASA POWER) + forecast (Open-Meteo) weather data."""
    return await get_combined_weather_data(lat, lon)
