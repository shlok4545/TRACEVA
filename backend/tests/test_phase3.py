import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture
def auth_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "nurse@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_category_retrieval(auth_headers):
    response = client.get("/api/waste-categories", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 5


def test_valid_classification(auth_headers):
    response = client.post(
        "/api/segregation/assess",
        json={
            "item_name": "used syringe",
            "item_description": "needle from emergency ward",
            "source_department": "Emergency",
            "contamination_indication": "blood stained",
            "quantity": 2,
            "condition": "intact",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"]
    assert body["segregation_group"]
    assert body["confidence"] >= 0.5
    assert body["requires_human_confirmation"] is False


def test_unknown_item(auth_headers):
    response = client.post(
        "/api/segregation/assess",
        json={
            "item_name": "mystery item with no known waste classification",
            "item_description": "unknown material",
            "source_department": "General",
            "contamination_indication": "unclear",
            "quantity": 1,
            "condition": "uncertain",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requires_human_confirmation"] is True
    assert "escalate" in body["warning"].lower() or "confirm" in body["warning"].lower()


def test_ambiguous_item(auth_headers):
    response = client.post(
        "/api/segregation/assess",
        json={
            "item_name": "contaminated container",
            "item_description": "plastic box with unknown contents",
            "source_department": "Ward",
            "contamination_indication": "possible biohazard",
            "quantity": 3,
            "condition": "damaged",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["requires_human_confirmation"] is True
    assert body["confidence"] < 0.9


def test_risk_calculation_high_risk():
    response = client.post(
        "/api/risk/assess",
        json={
            "waste_category": "Sharps",
            "contamination_level": "high",
            "quantity": 8,
            "waiting_duration_hours": 18,
            "damaged_seal": True,
            "leakage": True,
            "incident_flag": False,
            "urgency": "urgent",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] in {"HIGH", "CRITICAL"}
    assert body["score"] >= 60
    assert body["factors"]
    assert body["explanation"]


def test_risk_low_result():
    response = client.post(
        "/api/risk/assess",
        json={
            "waste_category": "Glass and Metal",
            "contamination_level": "low",
            "quantity": 1,
            "waiting_duration_hours": 2,
            "damaged_seal": False,
            "leakage": False,
            "incident_flag": False,
            "urgency": "routine",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] == "LOW"
    assert body["score"] <= 34


def test_risk_critical_result():
    response = client.post(
        "/api/risk/assess",
        json={
            "waste_category": "Pharmaceutical Hazardous Waste",
            "contamination_level": "severe",
            "quantity": 12,
            "waiting_duration_hours": 36,
            "damaged_seal": True,
            "leakage": True,
            "incident_flag": True,
            "urgency": "critical",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["priority"] == "CRITICAL"
    assert body["score"] >= 80


def test_invalid_request():
    response = client.post(
        "/api/segregation/assess",
        json={
            "item_name": "",
            "item_description": "",
            "source_department": "",
            "contamination_indication": "",
            "quantity": -1,
            "condition": "",
        },
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code in {401, 422}


def test_unauthorized_request():
    response = client.get("/api/waste-categories")
    assert response.status_code == 401


def test_authorized_classification_request(auth_headers):
    response = client.post(
        "/api/segregation/assess",
        json={
            "item_name": "blood-contaminated dressing",
            "item_description": "soiled dressing from ICU",
            "source_department": "ICU",
            "contamination_indication": "blood",
            "quantity": 4,
            "condition": "soiled",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "Infectious / Soiled Waste"
    assert body["requires_human_confirmation"] is False


def test_risk_config_endpoint(auth_headers):
    response = client.get("/api/risk/config", headers=auth_headers)
    assert response.status_code == 200


def test_deterministic_risk_output():
    payload = {
        "waste_category": "Sharps",
        "contamination_level": "high",
        "quantity": 5,
        "waiting_duration_hours": 12,
        "damaged_seal": True,
        "leakage": False,
        "incident_flag": False,
        "urgency": "urgent",
    }
    first = client.post("/api/risk/assess", json=payload).json()
    second = client.post("/api/risk/assess", json=payload).json()
    assert first == second
