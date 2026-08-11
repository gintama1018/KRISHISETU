"""
KrishiSetu — Weather & Soil Data Ingestion
Layer 1: Data Ingestion
Sources: NASA POWER API + Open-Meteo API
"""
import os
import httpx
from typing import Optional
from datetime import datetime, timedelta


NASA_POWER_URL = os.getenv("NASA_POWER_BASE_URL", "https://power.larc.nasa.gov/api/temporal/daily/point")
OPEN_METEO_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")


async def fetch_nasa_power(lat: float, lon: float, days_back: int = 30) -> dict:
    """Fetch historical weather + solar data from NASA POWER (free, no API key needed)."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    nasa_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
        "api_key": nasa_key,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(NASA_POWER_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    props = data.get("properties", {}).get("parameter", {})
    return {
        "source": "NASA POWER",
        "lat": lat,
        "lon": lon,
        "temperature_max": props.get("T2M_MAX", {}),
        "temperature_min": props.get("T2M_MIN", {}),
        "temperature_avg": props.get("T2M", {}),
        "precipitation_mm": props.get("PRECTOTCORR", {}),
        "solar_radiation": props.get("ALLSKY_SFC_SW_DWN", {}),
        "humidity_pct": props.get("RH2M", {}),
        "wind_speed_ms": props.get("WS2M", {}),
    }


async def fetch_open_meteo_forecast(lat: float, lon: float, days: int = 7) -> dict:
    """Fetch 7-day weather forecast from Open-Meteo (free, no API key)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,et0_fao_evapotranspiration",
        "hourly": "relativehumidity_2m,soil_moisture_0_1cm",
        "forecast_days": min(days, 16),
        "timezone": "Asia/Kolkata",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return {
        "source": "Open-Meteo",
        "lat": lat,
        "lon": lon,
        "forecast_daily": data.get("daily", {}),
        "soil_moisture_hourly": data.get("hourly", {}).get("relativehumidity_2m", []),
    }


async def get_combined_weather_data(lat: float, lon: float) -> dict:
    """Combine NASA historical + Open-Meteo forecast into one unified payload."""
    try:
        historical = await fetch_nasa_power(lat, lon, days_back=30)
    except Exception as e:
        historical = {"source": "NASA POWER", "error": str(e), "fallback": True}

    try:
        forecast = await fetch_open_meteo_forecast(lat, lon, days=7)
    except Exception as e:
        forecast = {"source": "Open-Meteo", "error": str(e), "fallback": True}

    return {"historical": historical, "forecast": forecast}
