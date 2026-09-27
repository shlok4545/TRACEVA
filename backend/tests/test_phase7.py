import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def ward_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "nurse@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def collector_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "collector@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def treatment_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "treatment@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_passport(headers):
    payload = {
        "facility_id": 1,
        "ward_id": 1,
        "items": [
            {
                "item_name": "blood contaminated dressing",
                "item_description": "soiled dressing from ICU",
                "source_department": "ICU",
                "contamination_level": "high",
                "condition": "soiled",
                "quantity": 3,
                "weight_kg": 0.9,
            }
        ],
    }
    response = client.post("/api/passports", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_phase7_incident_creation_and_dashboard(ward_headers, admin_headers):
    passport = _create_passport(ward_headers)
    response = client.post(
        "/api/incidents",
        json={
            "facility_id": 1,
            "passport_id": passport["id"],
            "incident_type": "DAMAGED_SEAL",
            "severity": "HIGH",
            "title": "Damaged seal during handover",
            "description": "The seal was torn before transfer.",
        },
        headers=ward_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["incident_type"] == "DAMAGED_SEAL"
    assert body["status"] == "OPEN"

    list_response = client.get("/api/incidents", headers=admin_headers)
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["items"]

    summary = client.get("/api/dashboard/summary", headers=admin_headers)
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert set(payload).issuperset({"passport_summary", "risk_summary", "pickup_summary", "treatment_summary", "incident_summary", "alerts", "recent_activity"})

    risk = client.get("/api/reports/risk", headers=admin_headers)
    assert risk.status_code == 200, risk.text
    assert set(risk.json()).issuperset({"low", "medium", "high", "critical"})

    pickups = client.get("/api/reports/pickups?range=today", headers=admin_headers)
    assert pickups.status_code == 200, pickups.text
    assert set(pickups.json()).issuperset({"total_requests", "completed", "pending", "overdue"})

    treatment = client.get("/api/reports/treatment", headers=admin_headers)
    assert treatment.status_code == 200, treatment.text
    assert set(treatment.json()).issuperset({"received_count", "treatment_pending", "treatment_completed", "verification_pending"})

    traceability = client.get("/api/reports/traceability", headers=admin_headers)
    assert traceability.status_code == 200, traceability.text
    assert "stages" in traceability.json()

    activity = client.get("/api/dashboard/activity", headers=admin_headers)
    assert activity.status_code == 200, activity.text
    assert isinstance(activity.json(), list)


def test_phase7_unauthorized_incident_scope(ward_headers, admin_headers):
    response = client.post(
        "/api/incidents",
        json={
            "facility_id": 4,
            "incident_type": "TREATMENT_DELAY",
            "severity": "MEDIUM",
            "title": "Unauthorized facility incident",
            "description": "This should be blocked.",
        },
        headers=ward_headers,
    )
    assert response.status_code in {403, 400}, response.text

    summary = client.get("/api/dashboard/summary", headers=ward_headers)
    assert summary.status_code == 200, summary.text
    assert isinstance(summary.json()["incident_summary"], dict)
