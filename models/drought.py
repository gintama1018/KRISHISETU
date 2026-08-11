"""
KrishiSetu — Drought Risk Scoring Model
Layer 3: AI Risk Models (extracted & re-architected from KISAN-AI)
"""
from typing import Optional


# Threshold constants — per-crop, tunable
DROUGHT_THRESHOLDS = {
    "default": {"precip_mm_30d": 50, "humidity_min_pct": 30, "temp_max_c": 38},
    "rice":    {"precip_mm_30d": 80, "humidity_min_pct": 40, "temp_max_c": 35},
    "wheat":   {"precip_mm_30d": 40, "humidity_min_pct": 25, "temp_max_c": 40},
    "cotton":  {"precip_mm_30d": 45, "humidity_min_pct": 30, "temp_max_c": 42},
    "maize":   {"precip_mm_30d": 60, "humidity_min_pct": 35, "temp_max_c": 38},
    "mustard": {"precip_mm_30d": 35, "humidity_min_pct": 20, "temp_max_c": 37},
    "soybean": {"precip_mm_30d": 55, "humidity_min_pct": 35, "temp_max_c": 36},
}


def score_drought_risk(
    precip_30d_mm: float,
    avg_humidity_pct: float,
    max_temp_c: float,
    crop: str = "default",
    soil_moisture_pct: Optional[float] = None,
) -> dict:
    """
    Compute drought risk score (0–100) for a given field.

    Scoring logic:
      - Precipitation deficit contributes 40 points
      - Humidity deficit contributes 30 points
      - High temperature contributes 20 points
      - Soil moisture deficit contributes 10 points (if available)
    """
    thresholds = DROUGHT_THRESHOLDS.get(crop.lower(), DROUGHT_THRESHOLDS["default"])

    # Precipitation score (0-40)
    precip_thresh = thresholds["precip_mm_30d"]
    if precip_30d_mm >= precip_thresh:
        precip_score = 0
    else:
        precip_score = min(40, int(40 * (1 - precip_30d_mm / precip_thresh)))

    # Humidity score (0-30)
    hum_thresh = thresholds["humidity_min_pct"]
    if avg_humidity_pct >= hum_thresh:
        hum_score = 0
    else:
        hum_score = min(30, int(30 * (1 - avg_humidity_pct / hum_thresh)))

    # Temperature score (0-20)
    temp_thresh = thresholds["temp_max_c"]
    if max_temp_c <= temp_thresh:
        temp_score = 0
    else:
        temp_score = min(20, int(20 * min(1.0, (max_temp_c - temp_thresh) / 10)))

    # Soil moisture score (0-10)
    if soil_moisture_pct is not None:
        if soil_moisture_pct >= 40:
            soil_score = 0
        else:
            soil_score = min(10, int(10 * (1 - soil_moisture_pct / 40)))
    else:
        soil_score = 5  # neutral if unknown

    total = precip_score + hum_score + temp_score + soil_score

    if total >= 70:
        level = "CRITICAL"
        color = "red"
    elif total >= 45:
        level = "HIGH"
        color = "orange"
    elif total >= 20:
        level = "MODERATE"
        color = "yellow"
    else:
        level = "LOW"
        color = "green"

    return {
        "score": total,
        "level": level,
        "color": color,
        "crop": crop,
        "breakdown": {
            "precipitation": precip_score,
            "humidity": hum_score,
            "temperature": temp_score,
            "soil_moisture": soil_score,
        },
        "inputs": {
            "precip_30d_mm": precip_30d_mm,
            "avg_humidity_pct": avg_humidity_pct,
            "max_temp_c": max_temp_c,
            "soil_moisture_pct": soil_moisture_pct,
        },
    }
