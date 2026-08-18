"""
KrishiSetu — Cross-Domain Correlation Module
Layer 3: AI Risk Models & Labor Scheduling Intelligence

Cross-Domain Correlation:
Heat/drought stress → Farm Labor scheduling advisory
(Tells farmers & field workers WHEN NOT to work the fields based on WBGT thresholds)
"""
from datetime import datetime, timezone

# Heat stress thresholds (°C) — WBGT-informed
HEAT_STRESS_LEVELS = [
    (27, "SAFE",    "green",  "Normal work hours. Keep water available."),
    (32, "CAUTION", "yellow", "Limit continuous work to 45-min cycles. Take 15-min shade breaks."),
    (35, "WARNING", "orange", "Restrict outdoor work to early morning (6–9 AM) and late evening (5–7 PM) only."),
    (38, "DANGER",  "red",    "No field work recommended. Risk of heat stroke. Stay indoors."),
    (99, "EXTREME", "darkred","Declare field rest day. Emergency water and cooling measures required."),
]


def get_labor_scheduling_advisory(
    max_temp_c: float,
    drought_score: int,
    humidity_pct: float,
    crop: str = "default",
) -> dict:
    """
    Correlate heat/drought stress with farm labor scheduling.
    Returns safe working hours + heat advisory.
    """
    # Feels-like heat index adjustment for humidity
    heat_index = max_temp_c
    if humidity_pct > 60:
        heat_index += (humidity_pct - 60) * 0.15  # simplified heat index bump

    # Determine stress level
    level_label = "SAFE"
    level_color = "green"
    advisory_text = ""
    for threshold, label, color, text in HEAT_STRESS_LEVELS:
        if heat_index <= threshold:
            level_label = label
            level_color = color
            advisory_text = text
            break

    # Drought stress modifier
    drought_modifier = ""
    if drought_score >= 70:
        drought_modifier = "⚠️ Severe drought conditions: prioritize water conservation — avoid irrigation during peak heat (11 AM–4 PM)."
    elif drought_score >= 45:
        drought_modifier = "Moderate drought: irrigate only early morning or evening."

    # Safe hours recommendation
    if heat_index <= 27:
        safe_hours = "All day (6 AM – 6 PM)"
    elif heat_index <= 32:
        safe_hours = "Morning (6–11 AM) and Evening (4–7 PM)"
    elif heat_index <= 35:
        safe_hours = "Early morning only (6–9 AM)"
    else:
        safe_hours = "No outdoor field work recommended today"

    return {
        "type": "labor_scheduling",
        "max_temp_c": max_temp_c,
        "heat_index_c": round(heat_index, 1),
        "humidity_pct": humidity_pct,
        "drought_score": drought_score,
        "heat_stress_level": level_label,
        "color": level_color,
        "safe_working_hours": safe_hours,
        "advisory": advisory_text,
        "drought_modifier": drought_modifier,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
