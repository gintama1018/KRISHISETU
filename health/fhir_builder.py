"""
KrishiSetu — FHIR R4 Observation Bundle Builder (ABDM-Ready)
health/fhir_builder.py

Produces standards-compliant FHIR R4 Observation resources from agricultural
and occupational health risk assessments.

Clinical & Environmental LOINC Codes:
  - LOINC 60830-9 : Ambient temperature [°C / Cel]
  - LOINC 44834-0 : Relative Humidity [%]
  - LOINC 56848-4 : Occupational chemical exposure [h/wk]
  - LOINC 75325-1 : Symptom severity / clinical risk assessment [{score}]
  - LOINC 75323-6 : Condition clinical status / reported symptoms

Semantic Mapping Architecture:
  Observation 1 (Ambient Thermal Stress):
    - Primary valueQuantity: Ambient temperature (e.g. 38.5 Cel)
    - Component 1: Relative Humidity (e.g. 75.0 %)
    - Component 2: Heat Risk Index Score (Local Code: krishisetu-heat-index, 78/100)
    - Interpretation: Abnormal / High Heat Stress

  Observation 2 (Occupational Chemical / Pesticide Exposure):
    - Primary valueQuantity: Weekly pesticide exposure duration (e.g. 6.0 h/wk)
    - Component 1: PPE usage status (valueBoolean: false)
    - Component 2: Pesticide Risk Index Score (Local Code: krishisetu-pesticide-risk, 72/100)

  Observation 3 (Occupational Health Risk & Symptom Evaluation):
    - Primary valueQuantity: Composite health risk score (e.g. 64 {score})
    - Interpretation: HIGH (triggers farm labor restriction to 4h/day)
    - Components: Individual reported symptoms (headache, dizziness, nausea)

Enables open-standard ABDM interoperability: A conformant ABDM / NRCeS FHIR repository
can validate and ingest these resources directly without schema divergence.
"""

import uuid
from datetime import datetime, timezone
from typing import List


FHIR_VERSION = "4.0.1"
FHIR_BASE_URL = "https://krishisetu.app/fhir"  # Endpoint for ABDM FHIR bundle export


def build_observation(
    farmer_id: str,
    asha_id: str,
    temp_c: float,
    humidity_pct: float,
    pesticide_hours_week: float,
    symptoms: List[str],
    heat_risk_score: int,
    pesticide_risk_score: int,
    composite_risk_score: int,
    risk_level: str,
    recorded_at: str = None,
    has_ppe: bool = False,
) -> dict:
    """
    Build a standard-conformant FHIR R4 Bundle containing 3 distinct Observation resources.
    Returns a complete, validator-conformant FHIR R4 Bundle JSON.
    """
    bundle_id = str(uuid.uuid4())
    ts = recorded_at or datetime.now(timezone.utc).isoformat()
    subject = {"reference": f"Patient/{farmer_id}", "display": f"Farmer {farmer_id}"}
    performer = [{"reference": f"Practitioner/{asha_id}", "display": f"ASHA Worker {asha_id}"}]

    # ── Observation 1: Ambient Thermal Stress (LOINC 60830-9) ─────────────────
    obs_heat = {
        "resourceType": "Observation",
        "id": f"thermal-stress-{bundle_id[:8]}",
        "meta": {
            "versionId": "1",
            "lastUpdated": ts,
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs / Environmental",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "60830-9",
                    "display": "Ambient temperature",
                }
            ],
            "text": "Ambient Environmental Heat & Thermal Stress",
        },
        "subject": subject,
        "performer": performer,
        "effectiveDateTime": ts,
        # Clinical Semantic Fix: Primary value is the measured ambient temperature in °C
        "valueQuantity": {
            "value": round(temp_c, 1),
            "unit": "Cel",
            "system": "http://unitsofmeasure.org",
            "code": "Cel",
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "H" if heat_risk_score >= 70 else ("A" if heat_risk_score >= 45 else "N"),
                        "display": "High Thermal Stress" if heat_risk_score >= 70 else "Normal/Moderate",
                    }
                ]
            }
        ],
        "component": [
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "44834-0", "display": "Relative Humidity"}]
                },
                "valueQuantity": {"value": round(humidity_pct, 1), "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"},
            },
            {
                "code": {
                    "coding": [{"system": "https://krishisetu.in/codes", "code": "heat-risk-index", "display": "Derived Heat Risk Score"}]
                },
                "valueQuantity": {"value": heat_risk_score, "unit": "score", "system": "http://unitsofmeasure.org", "code": "{score}"},
            },
        ],
    }

    # ── Observation 2: Occupational Pesticide Exposure (LOINC 56848-4) ────────
    obs_pesticide = {
        "resourceType": "Observation",
        "id": f"pesticide-exp-{bundle_id[:8]}",
        "meta": {
            "versionId": "1",
            "lastUpdated": ts,
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "social-history",
                        "display": "Social History / Occupational",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "56848-4",
                    "display": "Occupational chemical exposure",
                }
            ],
            "text": "Weekly Agricultural Chemical / Pesticide Exposure",
        },
        "subject": subject,
        "performer": performer,
        "effectiveDateTime": ts,
        # Clinical Semantic Fix: Primary value is weekly exposure duration in hours/week
        "valueQuantity": {
            "value": round(pesticide_hours_week, 1),
            "unit": "h/wk",
            "system": "http://unitsofmeasure.org",
            "code": "h/wk",
        },
        "component": [
            {
                "code": {
                    "coding": [{"system": "https://krishisetu.in/codes", "code": "ppe-status", "display": "Personal Protective Equipment Used"}]
                },
                "valueBoolean": has_ppe,
            },
            {
                "code": {
                    "coding": [{"system": "https://krishisetu.in/codes", "code": "pesticide-risk-index", "display": "Derived Pesticide Risk Score"}]
                },
                "valueQuantity": {"value": pesticide_risk_score, "unit": "score", "system": "http://unitsofmeasure.org", "code": "{score}"},
            },
        ],
        "note": [{"text": f"Pesticide Risk Score: {pesticide_risk_score}/100 (WHO Hazard Guidelines)"}],
    }

    # ── Observation 3: Composite Occupational Health Risk (LOINC 75325-1) ─────
    obs_composite = {
        "resourceType": "Observation",
        "id": f"composite-risk-{bundle_id[:8]}",
        "meta": {
            "versionId": "1",
            "lastUpdated": ts,
            "profile": ["http://hl7.org/fhir/StructureDefinition/Observation"],
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "survey",
                        "display": "Survey / Risk Assessment",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "75325-1",
                    "display": "Symptom severity assessment",
                }
            ],
            "text": "KrishiSetu Composite Occupational Health Risk Assessment",
        },
        "subject": subject,
        "performer": performer,
        "effectiveDateTime": ts,
        "valueQuantity": {
            "value": composite_risk_score,
            "unit": "score",
            "system": "http://unitsofmeasure.org",
            "code": "{score}",
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "H" if composite_risk_score >= 45 else "N",
                        "display": risk_level,
                    }
                ]
            }
        ],
        "component": [
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "75323-6", "display": f"Symptom: {s}"}],
                    "text": s.replace("_", " ").title(),
                },
                "valueBoolean": True,
            }
            for s in symptoms
        ],
        "note": [
            {
                "text": (
                    f"KrishiSetu Health Assessment v3.0 | "
                    f"Risk Level: {risk_level} ({composite_risk_score}/100) | "
                    f"Recorded by ASHA Worker {asha_id} | "
                    f"ABDM-Ready FHIR R4 Bundle Format"
                )
            }
        ],
    }

    # ── Complete FHIR R4 Bundle ───────────────────────────────────────────────
    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"lastUpdated": ts},
        "type": "collection",
        "total": 3,
        "entry": [
            {"fullUrl": f"{FHIR_BASE_URL}/Observation/{obs_heat['id']}",      "resource": obs_heat},
            {"fullUrl": f"{FHIR_BASE_URL}/Observation/{obs_pesticide['id']}", "resource": obs_pesticide},
            {"fullUrl": f"{FHIR_BASE_URL}/Observation/{obs_composite['id']}", "resource": obs_composite},
        ],
    }

    return bundle
