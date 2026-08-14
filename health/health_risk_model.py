"""
KrishiSetu — Health Risk Module
health/health_risk_model.py

Rule-based health risk scoring for ASHA workers.
Architecture mirrors drought/pest models (honest, auditable, threshold-based).

Inputs  : temp_c, humidity_pct, pesticide_hours_week, symptoms[]
Outputs : heat_risk_score (0-100), pesticide_risk_score (0-100),
          composite_risk_score, risk_level, recommended_action
"""

from typing import List


# ── Symptom severity weights ──────────────────────────────────────────────────
SYMPTOM_WEIGHTS = {
    "headache":          10,
    "dizziness":         15,
    "nausea":            15,
    "vomiting":          20,
    "skin_rash":         15,
    "eye_irritation":    10,
    "breathing_difficulty": 25,
    "chest_pain":        30,
    "fainting":          35,
    "muscle_cramps":     12,
    "excessive_sweating": 8,
    "confusion":         30,
}


def compute_heat_risk(temp_c: float, humidity_pct: float) -> int:
    """
    Heat stress index calculation.
    Based on NIOSH occupational heat exposure guidelines.
    Returns score 0-100.
    """
    # Wet Bulb Globe Temperature approximation (simplified)
    wbgt_approx = 0.567 * temp_c + 0.393 * (humidity_pct / 100 * 6.105 * (17.27 * temp_c / (237.7 + temp_c))) + 3.94

    if wbgt_approx >= 33:
        score = 90
    elif wbgt_approx >= 30:
        score = 70
    elif wbgt_approx >= 28:
        score = 50
    elif wbgt_approx >= 25:
        score = 30
    else:
        score = 10

    # Boost if raw temp is extreme
    if temp_c >= 42:
        score = min(100, score + 15)
    elif temp_c >= 38:
        score = min(100, score + 8)

    return score


def compute_pesticide_risk(pesticide_hours_week: float, has_ppe: bool = False) -> int:
    """
    Pesticide exposure risk.
    WHO Class II/III pesticide exposure guidelines.
    Returns score 0-100.
    """
    base = min(100, int(pesticide_hours_week * 12))  # 8.3hrs/week = ~100
    if has_ppe:
        base = int(base * 0.4)  # PPE reduces risk by ~60%
    return base


def compute_symptom_score(symptoms: List[str]) -> int:
    """Sum severity weights for reported symptoms. Cap at 100."""
    total = sum(SYMPTOM_WEIGHTS.get(s.lower().replace(" ", "_"), 5) for s in symptoms)
    return min(100, total)


def score_health_risk(
    temp_c: float,
    humidity_pct: float,
    pesticide_hours_week: float,
    symptoms: List[str],
    has_ppe: bool = False,
) -> dict:
    """
    Main health risk scoring function.
    Returns full structured health risk assessment.
    """
    heat_score       = compute_heat_risk(temp_c, humidity_pct)
    pesticide_score  = compute_pesticide_risk(pesticide_hours_week, has_ppe)
    symptom_score    = compute_symptom_score(symptoms)

    # Composite: weighted combination
    composite = int(0.35 * heat_score + 0.35 * pesticide_score + 0.30 * symptom_score)

    # Risk level classification
    if composite >= 70:
        risk_level = "CRITICAL"
        recommended_action = (
            "Immediate medical evaluation required. Stop all field work. "
            "Contact PHC or nearest ASHA supervisor immediately."
        )
        max_field_hours = 2
    elif composite >= 45:
        risk_level = "HIGH"
        recommended_action = (
            "Reduce pesticide exposure immediately. Ensure PPE usage. "
            "Rest in shade every 30 minutes. Drink ORS every hour."
        )
        max_field_hours = 4
    elif composite >= 20:
        risk_level = "MODERATE"
        recommended_action = (
            "Monitor symptoms. Avoid peak-heat field work (11 AM–3 PM). "
            "Increase water intake. Use PPE when spraying."
        )
        max_field_hours = 6
    else:
        risk_level = "LOW"
        recommended_action = (
            "Maintain standard precautions. Stay hydrated. "
            "Report any new symptoms to ASHA worker."
        )
        max_field_hours = 8

    return {
        "heat_risk_score":       heat_score,
        "pesticide_risk_score":  pesticide_score,
        "symptom_score":         symptom_score,
        "composite_risk_score":  composite,
        "risk_level":            risk_level,
        "recommended_action":    recommended_action,
        "max_safe_field_hours":  max_field_hours,
        "inputs": {
            "temp_c":                 temp_c,
            "humidity_pct":           humidity_pct,
            "pesticide_hours_week":   pesticide_hours_week,
            "symptoms":               symptoms,
            "has_ppe":                has_ppe,
        },
    }
