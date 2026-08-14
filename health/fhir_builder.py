"""
KrishiSetu — FHIR R4 Observation Builder
health/fhir_builder.py

Produces valid FHIR R4 Observation resources from health risk scores.
LOINC codes used:
  - 8310-5   : Body temperature
  - 56848-4  : Occupational chemical exposure
  - 72166-2  : Tobacco use status (repurposed here for pesticide exposure flag)
  - 75323-6  : Condition clinical status
  - 44261-6  : Patient Health Questionnaire (symptom checklist)

This enables ABDM/FHIR interoperability: a conformant FHIR server
(e.g., NRCeS ABDM SBX) can ingest these Observation resources directly.
"""

import uuid
from datetime import datetime, timezone
from typing import List


FHIR_VERSION = "4.0.1"
FHIR_BASE_URL = "https://krishisetu.app/fhir"  # Replace with ABDM SBX URL in production


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
) -> dict:
    """
    Build a FHIR R4 Bundle containing Observation resources.
    Returns a complete, validator-conformant FHIR R4 Bundle JSON.
    """
    obs_id   = str(uuid.uuid4())
    ts       = recorded_at or datetime.now(timezone.utc).isoformat()
    subject  = {"reference": f"Patient/{farmer_id}", "display": f"Farmer {farmer_id}"}
    performer= [{"reference": f"Practitioner/{asha_id}", "display": f"ASHA Worker {asha_id}"}]

    # ── Observation 1: Heat Risk Score ────────────────────────────────────────
    obs_heat = {
        "resourceType": "Observation",
        "id": f"heat-risk-{obs_id[:8]}",
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
                        "display": "Social History",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8310-5",
                    "display": "Body temperature",
                }
            ],
            "text": "Heat Exposure Risk Score (KrishiSetu)",
        },
        "subject": subject,
        "performer": performer,
        "effectiveDateTime": ts,
        "valueQuantity": {
            "value": heat_risk_score,
            "unit": "score",
            "system": "http://unitsofmeasure.org",
            "code": "{score}",
        },
        "interpretation": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "H" if heat_risk_score >= 70 else ("HH" if heat_risk_score >= 90 else "N"),
                        "display": risk_level,
                    }
                ]
            }
        ],
        "component": [
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "60830-9", "display": "Ambient temperature"}]
                },
                "valueQuantity": {"value": temp_c, "unit": "Cel", "system": "http://unitsofmeasure.org", "code": "Cel"},
            },
            {
                "code": {
                    "coding": [{"system": "http://loinc.org", "code": "44834-0", "display": "Humidity"}]
                },
                "valueQuantity": {"value": humidity_pct, "unit": "%", "system": "http://unitsofmeasure.org", "code": "%"},
            },
        ],
    }

    # ── Observation 2: Pesticide Exposure ─────────────────────────────────────
    obs_pesticide = {
        "resourceType": "Observation",
        "id": f"pesticide-{obs_id[:8]}",
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
                        "display": "Social History",
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
            "text": "Weekly Pesticide Exposure Hours",
        },
        "subject": subject,
        "performer": performer,
        "effectiveDateTime": ts,
        "valueQuantity": {
            "value": pesticide_hours_week,
            "unit": "h/wk",
            "system": "http://unitsofmeasure.org",
            "code": "h/wk",
        },
        "note": [{"text": f"Pesticide Risk Score: {pesticide_risk_score}/100 (KrishiSetu rule-based model)"}],
    }

    # ── Observation 3: Composite Health Risk + Symptom checklist ─────────────
    obs_composite = {
        "resourceType": "Observation",
        "id": f"composite-{obs_id[:8]}",
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
                        "display": "Survey",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "44261-6",
                    "display": "Patient Health Questionnaire",
                }
            ],
            "text": "Composite Occupational Health Risk (KrishiSetu ASHA Assessment)",
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
                "code": {"text": f"Symptom: {s}"},
                "valueBoolean": True,
            }
            for s in symptoms
        ],
        "note": [
            {
                "text": (
                    f"KrishiSetu Health Risk Assessment v1.0 | "
                    f"Risk Level: {risk_level} | "
                    f"Recorded by ASHA {asha_id} | "
                    f"FHIR R4 format for ABDM interoperability"
                )
            }
        ],
    }

    # ── FHIR Bundle ───────────────────────────────────────────────────────────
    bundle = {
        "resourceType": "Bundle",
        "id": obs_id,
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
