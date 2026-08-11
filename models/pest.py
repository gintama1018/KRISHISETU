"""
KrishiSetu — Pest Risk Scoring Model
Layer 3: AI Risk Models (extracted & re-architected from KISAN-AI)
"""
from typing import Optional


# Pest risk thresholds — indexed by crop
PEST_THRESHOLDS = {
    "default": {"humidity_trigger_pct": 70, "temp_range": (22, 32), "consecutive_humid_days": 3},
    "rice":    {"humidity_trigger_pct": 75, "temp_range": (25, 35), "consecutive_humid_days": 2},
    "wheat":   {"humidity_trigger_pct": 65, "temp_range": (18, 28), "consecutive_humid_days": 4},
    "cotton":  {"humidity_trigger_pct": 70, "temp_range": (20, 35), "consecutive_humid_days": 3},
    "maize":   {"humidity_trigger_pct": 72, "temp_range": (22, 32), "consecutive_humid_days": 3},
    "soybean": {"humidity_trigger_pct": 75, "temp_range": (22, 30), "consecutive_humid_days": 3},
}

# Common pests by crop
COMMON_PESTS = {
    "rice":    ["Brown Plant Hopper", "Stem Borer", "Leaf Folder", "Blast Fungus"],
    "wheat":   ["Aphid", "Rust Fungus", "Powdery Mildew", "Termite"],
    "cotton":  ["Bollworm", "Whitefly", "Aphid", "Thrips"],
    "maize":   ["Fall Army Worm", "Stem Borer", "Grey Leaf Spot"],
    "soybean": ["Pod Borer", "Whitefly", "Aphid", "Rust Fungus"],
    "default": ["Aphid", "Stem Borer", "Leaf Spot Fungus"],
}


def score_pest_risk(
    avg_humidity_pct: float,
    avg_temp_c: float,
    consecutive_humid_days: int,
    crop: str = "default",
    recent_rain_events: int = 0,
) -> dict:
    """
    Compute pest outbreak risk score (0–100).

    Scoring logic:
      - Humidity above trigger: 35 points
      - Temperature in optimal pest range: 30 points
      - Consecutive humid days: 25 points
      - Recent rain events (fungal risk): 10 points
    """
    thresholds = PEST_THRESHOLDS.get(crop.lower(), PEST_THRESHOLDS["default"])
    hum_trigger = thresholds["humidity_trigger_pct"]
    t_min, t_max = thresholds["temp_range"]
    humid_day_thresh = thresholds["consecutive_humid_days"]

    # Humidity score (0-35)
    if avg_humidity_pct >= hum_trigger:
        hum_score = min(35, int(35 * (avg_humidity_pct - hum_trigger + 5) / 20))
    else:
        hum_score = 0

    # Temperature score (0-30)
    if t_min <= avg_temp_c <= t_max:
        # Perfect pest range — max score
        temp_score = 30
    elif avg_temp_c < t_min:
        temp_score = max(0, int(30 * (1 - (t_min - avg_temp_c) / 10)))
    else:
        temp_score = max(0, int(30 * (1 - (avg_temp_c - t_max) / 10)))

    # Consecutive humid days (0-25)
    if consecutive_humid_days >= humid_day_thresh:
        day_score = min(25, int(25 * consecutive_humid_days / (humid_day_thresh + 3)))
    else:
        day_score = int(25 * consecutive_humid_days / humid_day_thresh) if humid_day_thresh > 0 else 0

    # Rain events score (0-10)
    rain_score = min(10, recent_rain_events * 3)

    total = hum_score + temp_score + day_score + rain_score

    if total >= 65:
        level = "CRITICAL"
        color = "red"
        likely_pests = COMMON_PESTS.get(crop.lower(), COMMON_PESTS["default"])[:3]
    elif total >= 40:
        level = "HIGH"
        color = "orange"
        likely_pests = COMMON_PESTS.get(crop.lower(), COMMON_PESTS["default"])[:2]
    elif total >= 20:
        level = "MODERATE"
        color = "yellow"
        likely_pests = COMMON_PESTS.get(crop.lower(), COMMON_PESTS["default"])[:1]
    else:
        level = "LOW"
        color = "green"
        likely_pests = []

    return {
        "score": total,
        "level": level,
        "color": color,
        "crop": crop,
        "likely_pests": likely_pests,
        "breakdown": {
            "humidity": hum_score,
            "temperature": temp_score,
            "consecutive_humid_days": day_score,
            "rain_events": rain_score,
        },
        "inputs": {
            "avg_humidity_pct": avg_humidity_pct,
            "avg_temp_c": avg_temp_c,
            "consecutive_humid_days": consecutive_humid_days,
            "recent_rain_events": recent_rain_events,
        },
    }
