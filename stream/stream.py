"""
KrishiSetu — Streaming / Recompute Engine
Layer 2: Pathway-pattern (normalize → threshold_check → alert_emit)
Uses asyncio queues to mimic Pathway's streaming pipeline.
"""
import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional
from models.drought import score_drought_risk
from models.pest import score_pest_risk


# ─── Normalize ────────────────────────────────────────────────────────────────

def normalize_weather_record(raw: dict) -> dict:
    """
    Normalize raw weather data from any source into a uniform internal record.
    Output shape is fixed regardless of source (NASA POWER / Open-Meteo / mock).
    """
    return {
        "lat": raw.get("lat", 0.0),
        "lon": raw.get("lon", 0.0),
        "farmer_id": raw.get("farmer_id"),
        "village_code": raw.get("village_code"),
        "crop": raw.get("crop", "default"),
        "precip_30d_mm": float(raw.get("precip_30d_mm") or raw.get("precipitation_mm", 0)),
        "precip_7d_mm": float(raw.get("precip_7d_mm", 0)),
        "avg_temp_c": float(raw.get("avg_temp_c") or raw.get("temperature_avg", 25)),
        "max_temp_c": float(raw.get("max_temp_c") or raw.get("temperature_max", 30)),
        "avg_humidity_pct": float(raw.get("avg_humidity_pct") or raw.get("humidity_pct", 50)),
        "consecutive_humid_days": int(raw.get("consecutive_humid_days", 0)),
        "recent_rain_events": int(raw.get("recent_rain_events", 0)),
        "soil_moisture_pct": raw.get("soil_moisture_pct"),
        "source": raw.get("source", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Threshold Check ──────────────────────────────────────────────────────────

def threshold_check(record: dict) -> dict:
    """
    Run all risk models on a normalized record and attach risk scores.
    """
    drought = score_drought_risk(
        precip_30d_mm=record["precip_30d_mm"],
        avg_humidity_pct=record["avg_humidity_pct"],
        max_temp_c=record["max_temp_c"],
        crop=record["crop"],
        soil_moisture_pct=record.get("soil_moisture_pct"),
    )
    pest = score_pest_risk(
        avg_humidity_pct=record["avg_humidity_pct"],
        avg_temp_c=record["avg_temp_c"],
        consecutive_humid_days=record["consecutive_humid_days"],
        crop=record["crop"],
        recent_rain_events=record["recent_rain_events"],
    )

    record["risk"] = {
        "drought": drought,
        "pest": pest,
        "composite_level": _composite_level(drought["level"], pest["level"]),
        "alert_required": drought["level"] in ("HIGH", "CRITICAL") or pest["level"] in ("HIGH", "CRITICAL"),
    }
    return record


def _composite_level(drought_level: str, pest_level: str) -> str:
    order = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1}
    d = order.get(drought_level, 1)
    p = order.get(pest_level, 1)
    combined = max(d, p)
    return {4: "CRITICAL", 3: "HIGH", 2: "MODERATE", 1: "LOW"}[combined]


# ─── Alert Emitter ────────────────────────────────────────────────────────────

class AlertEmitter:
    """Collects alerts and dispatches them to registered handlers."""

    def __init__(self):
        self._handlers: list[Callable] = []
        self._alert_log: list[dict] = []

    def register_handler(self, handler: Callable):
        self._handlers.append(handler)

    async def emit(self, record: dict):
        if not record.get("risk", {}).get("alert_required"):
            return
        alert = {
            "farmer_id": record.get("farmer_id"),
            "village_code": record.get("village_code"),
            "crop": record.get("crop"),
            "composite_level": record["risk"]["composite_level"],
            "drought_score": record["risk"]["drought"]["score"],
            "pest_score": record["risk"]["pest"]["score"],
            "lat": record["lat"],
            "lon": record["lon"],
            "timestamp": record["timestamp"],
        }
        self._alert_log.append(alert)
        for handler in self._handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(alert)
            else:
                handler(alert)
        return alert

    def get_recent_alerts(self, limit: int = 50) -> list:
        return self._alert_log[-limit:]


# ─── Pipeline ─────────────────────────────────────────────────────────────────

_emitter = AlertEmitter()


async def process_record(raw_record: dict) -> dict:
    """
    Full pipeline: normalize → threshold_check → alert_emit.
    Returns the enriched record with risk scores attached.
    """
    normalized = normalize_weather_record(raw_record)
    scored = threshold_check(normalized)
    await _emitter.emit(scored)
    return scored


def get_alert_emitter() -> AlertEmitter:
    return _emitter
