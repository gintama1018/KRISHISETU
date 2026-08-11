"""
KrishiSetu — Sowing Window Advisory Model
Layer 3: AI Risk Models (extracted & re-architected from KISAN-AI)
"""
from datetime import datetime
from typing import Optional


# Optimal sowing windows by crop (month ranges) — India-centric
SOWING_WINDOWS = {
    "rice":    {"kharif": (6, 8),   "rabi": None,       "zaid": None},
    "wheat":   {"kharif": None,     "rabi": (10, 12),   "zaid": None},
    "maize":   {"kharif": (5, 7),   "rabi": (10, 11),   "zaid": (2, 3)},
    "cotton":  {"kharif": (4, 6),   "rabi": None,       "zaid": None},
    "mustard": {"kharif": None,     "rabi": (10, 11),   "zaid": None},
    "soybean": {"kharif": (6, 7),   "rabi": None,       "zaid": None},
    "potato":  {"kharif": None,     "rabi": (10, 12),   "zaid": (1, 2)},
    "default": {"kharif": (6, 9),   "rabi": (10, 12),   "zaid": (2, 4)},
}

# Minimum weather conditions required for sowing
SOWING_CONDITIONS = {
    "rice":    {"min_temp_c": 20, "max_temp_c": 35, "min_precip_mm": 50, "min_humidity_pct": 60},
    "wheat":   {"min_temp_c": 10, "max_temp_c": 25, "min_precip_mm": 20, "min_humidity_pct": 40},
    "maize":   {"min_temp_c": 18, "max_temp_c": 33, "min_precip_mm": 30, "min_humidity_pct": 50},
    "cotton":  {"min_temp_c": 20, "max_temp_c": 38, "min_precip_mm": 25, "min_humidity_pct": 40},
    "soybean": {"min_temp_c": 18, "max_temp_c": 32, "min_precip_mm": 40, "min_humidity_pct": 55},
    "default": {"min_temp_c": 15, "max_temp_c": 35, "min_precip_mm": 30, "min_humidity_pct": 45},
}


def evaluate_sowing_window(
    crop: str,
    avg_temp_c: float,
    precip_7d_mm: float,
    avg_humidity_pct: float,
    current_month: Optional[int] = None,
) -> dict:
    """
    Evaluate whether current conditions are suitable for sowing.
    Returns a recommendation: OPTIMAL / ACCEPTABLE / WAIT / NOT_RECOMMENDED
    """
    month = current_month or datetime.now().month
    crop_lower = crop.lower()
    windows = SOWING_WINDOWS.get(crop_lower, SOWING_WINDOWS["default"])
    conditions = SOWING_CONDITIONS.get(crop_lower, SOWING_CONDITIONS["default"])

    # Determine current season
    season = "kharif" if 4 <= month <= 9 else "rabi"
    season_window = windows.get(season)

    in_season = False
    if season_window:
        in_season = season_window[0] <= month <= season_window[1]

    # Check weather conditions
    temp_ok = conditions["min_temp_c"] <= avg_temp_c <= conditions["max_temp_c"]
    precip_ok = precip_7d_mm >= conditions["min_precip_mm"]
    hum_ok = avg_humidity_pct >= conditions["min_humidity_pct"]

    conditions_met = sum([temp_ok, precip_ok, hum_ok])

    if in_season and conditions_met == 3:
        recommendation = "OPTIMAL"
        confidence = "HIGH"
    elif in_season and conditions_met == 2:
        recommendation = "ACCEPTABLE"
        confidence = "MEDIUM"
    elif in_season and conditions_met <= 1:
        recommendation = "WAIT"
        confidence = "MEDIUM"
    else:
        recommendation = "NOT_RECOMMENDED"
        confidence = "HIGH"

    # Next sowing window info
    next_window_months = None
    for s, w in windows.items():
        if w and (not season_window or s != season):
            next_window_months = w

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "crop": crop,
        "current_month": month,
        "current_season": season,
        "in_sowing_window": in_season,
        "conditions_check": {
            "temperature": {"ok": temp_ok, "value": avg_temp_c,
                            "required": f"{conditions['min_temp_c']}–{conditions['max_temp_c']}°C"},
            "precipitation_7d": {"ok": precip_ok, "value": precip_7d_mm,
                                  "required": f"≥{conditions['min_precip_mm']}mm"},
            "humidity": {"ok": hum_ok, "value": avg_humidity_pct,
                         "required": f"≥{conditions['min_humidity_pct']}%"},
        },
        "next_sowing_window": {
            "months": next_window_months,
            "label": f"Month {next_window_months[0]}–{next_window_months[1]}" if next_window_months else "N/A",
        },
    }
