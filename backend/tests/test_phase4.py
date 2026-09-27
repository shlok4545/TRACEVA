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


def test_passport_creation_and_items(auth_headers):
    response = client.post(
        "/api/passports",
        json={
            "facility_id": 1,
            "ward_id": 1,
            "items": [
                {
                    "item_name": "used syringe",
                    "item_description": "needle from emergency ward",
                    "source_department": "Emergency",
                    "contamination_level": "high",
                    "condition": "intact",
                    "quantity": 2,
                    "weight_kg": 0.4,
                }
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passport_number"].startswith("TRV-")
    assert body["status"] == "DRAFT"
    assert len(body["items"]) == 1
    assert body["items"][0]["item_name"] == "used syringe"
    return body


def test_passport_number_uniqueness(auth_headers):
    first = client.post(
        "/api/passports",
        json={"facility_id": 1, "ward_id": 1, "items": [{"item_name": "blood bag", "item_description": "soiled bag", "source_department": "ICU", "contamination_level": "moderate", "condition": "sealed", "quantity": 1, "weight_kg": 0.7}]},
        headers=auth_headers,
    )
    second = client.post(
        "/api/passports",
        json={"facility_id": 1, "ward_id": 1, "items": [{"item_name": "glass vial", "item_description": "broken vial", "source_department": "Pathology", "contamination_level": "low", "condition": "damaged", "quantity": 1, "weight_kg": 0.3}]},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["passport_number"] != second.json()["passport_number"]


def test_classify_and_risk_integration(auth_headers):
    passport_response = client.post(
        "/api/passports",
        json={"facility_id": 1, "ward_id": 1, "items": [{"item_name": "blood-contaminated dressing", "item_description": "soiled dressing from ICU", "source_department": "ICU", "contamination_level": "high", "condition": "soiled", "quantity": 4, "weight_kg": 1.2}]},
        headers=auth_headers,
    )
    passport_id = passport_response.json()["id"]

    classification = client.post(f"/api/passports/{passport_id}/classify", headers=auth_headers)
    assert classification.status_code == 200, classification.text
    assert classification.json()["status"] == "CLASSIFIED"
    assert classification.json()["classified_items"][0]["category"] == "Infectious / Soiled Waste"

    risk = client.post(f"/api/passports/{passport_id}/risk", headers=auth_headers)
    assert risk.status_code == 200, risk.text
    assert risk.json()["risk_priority"] in {"HIGH", "CRITICAL", "MEDIUM"}


def test_qr_generation_and_validation(auth_headers):
    passport_response = client.post(
        "/api/passports",
        json={"facility_id": 1, "ward_id": 1, "items": [{"item_name": "needle", "item_description": "used sharp", "source_department": "Emergency", "contamination_level": "high", "condition": "intact", "quantity": 3, "weight_kg": 0.2}]},
        headers=auth_headers,
    )
    passport_id = passport_response.json()["id"]

    generated = client.post(f"/api/passports/{passport_id}/generate-qr", headers=auth_headers)
    assert generated.status_code == 200, generated.text
    body = generated.json()
    assert body["qr_token"]
    assert body["qr_data_url"].startswith("data:image/png")

    validated = client.post("/api/qr/validate", json={"token": body["qr_token"]})
    assert validated.status_code == 200, validated.text
    assert validated.json()["passport_number"] == body["passport_number"]

    invalid = client.post("/api/qr/validate", json={"token": "bad-token"})
    assert invalid.status_code in {400, 404}


def test_status_transition_and_history(auth_headers):
    passport_response = client.post(
        "/api/passports",
        json={"facility_id": 1, "ward_id": 1, "items": [{"item_name": "glass vial", "item_description": "damaged glass", "source_department": "Pathology", "contamination_level": "low", "condition": "damaged", "quantity": 1, "weight_kg": 0.3}]},
        headers=auth_headers,
    )
    passport_id = passport_response.json()["id"]

    classify = client.post(f"/api/passports/{passport_id}/classify", headers=auth_headers)
    assert classify.status_code == 200

    valid_transition = client.post(f"/api/passports/{passport_id}/status", json={"status": "READY_FOR_PICKUP"}, headers=auth_headers)
    assert valid_transition.status_code == 200, valid_transition.text
    assert valid_transition.json()["status"] == "READY_FOR_PICKUP"

    invalid_transition = client.post(f"/api/passports/{passport_id}/status", json={"status": "DRAFT"}, headers=auth_headers)
    assert invalid_transition.status_code in {400, 409}

    events = client.get(f"/api/passports/{passport_id}/events", headers=auth_headers)
    assert events.status_code == 200, events.text
    assert len(events.json()) >= 2


def test_passport_listing_and_filters(auth_headers):
    response = client.get("/api/passports?status=DRAFT&risk_priority=LOW", headers=auth_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload, list)


def test_facility_authorization(auth_headers):
    wrong_facility = client.post(
        "/api/passports",
        json={"facility_id": 2, "ward_id": 6, "items": [{"item_name": "used swab", "item_description": "clinic item", "source_department": "Emergency", "contamination_level": "moderate", "condition": "sealed", "quantity": 1, "weight_kg": 0.2}]},
        headers=auth_headers,
    )
    assert wrong_facility.status_code in {403, 404}
