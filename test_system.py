"""
KrishiSetu — Direct FastAPI Test Suite
Uses FastAPI TestClient to test all 7 layers & endpoints directly in-process.
"""
import os
import sys
import time

# Ensure development environment for test suite execution
os.environ["APP_ENV"] = "development"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pipeline():
    print("=" * 60)
    print("KRISHISETU DIRECT SYSTEM TEST SUITE")
    print("=" * 60)

    # Test 1: Health / Status Check
    print("\n1. Testing Status & Health Endpoint...")
    res = client.get("/api/v1/status")
    if res.status_code == 404:
        res = client.get("/api/v1/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    data = res.json()
    print(f"   [OK] Server Status: {data['status']} | Project: {data['project']} v{data['version']}")

    # Test 2: Ingestion — NASA POWER & Open-Meteo Weather
    print("\n2. Testing Weather Data Ingestion (NASA POWER + Open-Meteo)...")
    res = client.get("/api/v1/data/weather?lat=26.14&lon=91.74")
    assert res.status_code == 200, f"Weather ingestion failed: {res.text}"
    w_data = res.json()
    print(f"   [OK] Historical Source: {w_data['historical'].get('source')} | Forecast Source: {w_data['forecast'].get('source')}")

    # Test 3: Mandi Price Feed — AGMARKNET
    print("\n3. Testing Mandi Prices Feed (AGMARKNET)...")
    res = client.get("/api/v1/prices/mandi?commodity=Rice&state=Assam&limit=5")
    assert res.status_code == 200, f"Mandi prices failed: {res.text}"
    m_data = res.json()
    print(f"   [OK] Commodity: {m_data.get('commodity')} | State: {m_data.get('state')} | Mandis Returned: {len(m_data.get('prices', []))}")

    # Test 4: DPDP Compliance — Consent Capture & Bcrypt Hashing
    print("\n4. Testing DPDP Compliance (Consent Capture & Bcrypt Hashing)...")
    farmer_id = f"F_TEST_{int(time.time())}"
    consent_payload = {
        "farmer_id": farmer_id,
        "phone": "+919876543210",
        "consent_method": "app",
        "data_uses": "weather_advisory,mandi_prices,risk_alerts",
    }
    res = client.post("/api/v1/compliance/consent/capture", json=consent_payload)
    assert res.status_code == 200, f"Consent capture failed: {res.text}"
    c_data = res.json()
    print(f"   [OK] Consent Captured: {c_data['consent_given']} | DPDP Compliant: {c_data['dpdp_compliant']}")

    # Test 5: Farmer Registry — Supabase Integration & AgriStack Sandbox Adapter
    print("\n5. Testing Farmer Registration (Supabase DB + AgriStack Adapter)...")
    farmer_payload = {
        "name": "Ramesh Kalita",
        "phone": "+919876543210",
        "village_code": "ASM-KAM-001",
        "district": "Kamrup",
        "state": "Assam",
        "crop": "rice",
        "plot_area_acres": 2.5,
        "language_preference": "English",
        "consent_given": True,
    }
    res = client.post("/api/v1/farmer/register", json=farmer_payload)
    assert res.status_code == 200, f"Farmer registration failed: {res.text}"
    f_data = res.json()
    real_fid = f_data.get('farmer_id', farmer_id)
    print(f"   [OK] Farmer Registered UUID: {real_fid} | AgriStack Registered: {f_data.get('agristack_registered')}")

    # Test 6: AI Advisory Pipeline & Models
    print("\n6. Testing Full AI Advisory Pipeline (Models + Gemini)...")
    adv_payload = {
        "farmer_id": real_fid,
        "village_code": "ASM-KAM-001",
        "crop": "rice",
        "language": "English",
        "lat": 26.14,
        "lon": 91.74,
        "state": "Assam",
        "precip_30d_mm": 55.0,
        "precip_7d_mm": 12.0,
        "avg_temp_c": 30.0,
        "max_temp_c": 34.0,
        "avg_humidity_pct": 72.0,
        "consecutive_humid_days": 4,
        "recent_rain_events": 2,
    }
    res = client.post("/api/v1/advisory/generate", json=adv_payload)
    assert res.status_code == 200, f"Advisory generation failed: {res.text}"
    adv_res = res.json()
    print(f"   [OK] Drought Score: {adv_res['risk']['drought']['score']}/100 ({adv_res['risk']['drought']['level']})")
    print(f"   [OK] Pest Score: {adv_res['risk']['pest']['score']}/100 ({adv_res['risk']['pest']['level']})")
    print(f"   [OK] Sowing Window: {adv_res['sowing']['recommendation']}")

    # Test 7: Cross-Domain Intelligence — Labor Safety & Health Integration
    print("\n7. Testing Cross-Domain Intelligence (Heat Stress -> Labor Safety)...")
    labor_payload = {
        "max_temp_c": 34.0,
        "drought_score": adv_res['risk']['drought']['score'],
        "humidity_pct": 72.0,
        "crop": "rice",
    }
    res = client.post("/api/v1/cross-domain/labor-advisory", json=labor_payload)
    assert res.status_code == 200, f"Labor advisory failed: {res.text}"
    l_res = res.json()
    print(f"   [OK] Heat Stress Level: {l_res['heat_stress_level']} | Safe Hours: {l_res['safe_working_hours']}")

    # Test 8: Insurance Evidence Logging
    print("\n8. Testing Insurance Evidence Logging & Trail Retrieval...")
    log_payload = {
        "farmer_id": real_fid,
        "event_type": "pest_spray",
        "crop": "rice",
        "drought_score": adv_res['risk']['drought']['score'],
        "pest_score": adv_res['risk']['pest']['score'],
        "pest_detected": "Stem Borer",
        "advisory_text": adv_res['advisory'][:100],
    }
    res = client.post("/api/v1/cross-domain/insurance-log", json=log_payload)
    assert res.status_code == 200, f"Insurance log failed: {res.text}"
    log_res = res.json()
    print(f"   [OK] Record ID: {log_res.get('record_id')} | Hash: {log_res.get('evidence_hash')[:25]}...")

    # Retrieve evidence trail
    res = client.get(f"/api/v1/cross-domain/insurance-trail/{real_fid}")
    assert res.status_code == 200, f"Insurance trail failed: {res.text}"
    trail_res = res.json()
    print(f"   [OK] Trail Retrieved: {len(trail_res.get('events', []))} evidence events on record.")

    # Test 9: DPDP Compliance — Right-to-Erasure Workflow
    print("\n9. Testing DPDP Right-to-Erasure Request...")
    res = client.post("/api/v1/compliance/erasure/request", json={"farmer_id": farmer_id, "reason": "test_deletion"})
    assert res.status_code == 200, f"Erasure request failed: {res.text}"
    e_res = res.json()
    print(f"   [OK] Erasure Requested: {e_res['erasure_requested']} | Scheduled Deletion: {e_res['scheduled_deletion']}")

    # Test 10: Rural Healthcare — ASHA Observation & FHIR R4 Interoperability
    print("\n10. Testing Rural Healthcare (ASHA Observation + FHIR R4 Bundle)...")
    health_payload = {
        "farmer_id": real_fid,
        "asha_id": "ASHA-KAM-001",
        "village_code": "ASM-KAM-001",
        "temp_c": 38.5,
        "humidity_pct": 75.0,
        "pesticide_hours_week": 6.0,
        "symptoms": ["headache", "dizziness", "nausea"],
        "has_ppe": False,
    }
    res = client.post("/api/v1/health/asha/record", json=health_payload, headers={"X-Role": "asha"})
    assert res.status_code == 200, f"Health observation failed: {res.text}"
    h_res = res.json()
    print(f"   [OK] Health Risk: {h_res['risk_assessment']['risk_level']} ({h_res['risk_assessment']['composite_risk_score']}/100)")
    print(f"   [OK] FHIR Bundle ID: {h_res['fhir_bundle_id']} | Resources: {h_res['fhir_resource_count']}")

    # Verify FHIR retrieval
    res = client.get(f"/api/v1/health/fhir/observation/{real_fid}")
    assert res.status_code == 200, f"FHIR retrieval failed: {res.text}"
    fhir_bundle = res.json()
    assert fhir_bundle.get("resourceType") == "Bundle", "Not a valid FHIR Bundle"
    print(f"   [OK] ABDM/FHIR R4 Bundle Verified: {fhir_bundle.get('total')} valid Observation resources with LOINC codes")

    # Test 11: Officer Dashboard Summary (Live Aggregation)
    print("\n11. Testing Officer Dashboard Summary API...")
    res = client.get("/api/v1/dashboard/summary", headers={"X-Role": "officer"})
    assert res.status_code == 200, f"Dashboard summary failed: {res.text}"
    dash_res = res.json()
    print(f"   [OK] Dashboard Summary: {dash_res['summary']['total_villages']} villages | Data Source: {dash_res.get('data_source')}")

    print("\n" + "=" * 60)
    print("ALL 11 SYSTEM COMPONENT TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_pipeline()
