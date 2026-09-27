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
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def collector_headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "collector@traceva.demo", "password": "Traceva@2026"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_passport(headers):
    payload = {
        "facility_id": 1,
        "ward_id": 1,
        "items": [
            {
                "item_name": "blood-contaminated dressing",
                "item_description": "soiled dressing from ICU",
                "source_department": "ICU",
                "contamination_level": "high",
                "condition": "soiled",
                "quantity": 4,
                "weight_kg": 1.2,
            }
        ],
    }
    response = client.post("/api/passports", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_pickup_request_creation_and_duplicate(ward_headers):
    passport = _create_passport(ward_headers)
    passport_id = passport["id"]
    response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport_id},
        headers=ward_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passport_id"] == passport_id
    assert body["status"] in {"REQUESTED", "QUEUED"}

    duplicate = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport_id},
        headers=ward_headers,
    )
    assert duplicate.status_code in {400, 409}, duplicate.text


def test_queue_and_filters(ward_headers, admin_headers):
    passport = _create_passport(ward_headers)
    request_response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport["id"]},
        headers=ward_headers,
    )
    assert request_response.status_code == 200, request_response.text

    queue = client.get("/api/pickups/queue", headers=admin_headers)
    assert queue.status_code == 200, queue.text
    queue_body = queue.json()
    assert isinstance(queue_body, list)
    assert any(item["passport_number"] == passport["passport_number"] for item in queue_body)

    filtered = client.get("/api/pickups/requests?status=REQUESTED&facility=1", headers=admin_headers)
    assert filtered.status_code == 200, filtered.text
    assert isinstance(filtered.json(), list)


def test_collector_assignment_and_workflow(collector_headers, admin_headers, ward_headers):
    passport = _create_passport(ward_headers)
    request_response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport["id"]},
        headers=ward_headers,
    )
    assert request_response.status_code == 200, request_response.text
    pickup_id = request_response.json()["id"]

    assign = client.post(
        f"/api/pickups/{pickup_id}/assign",
        json={"collector_id": 1},
        headers=admin_headers,
    )
    assert assign.status_code == 200, assign.text
    assert assign.json()["status"] == "ASSIGNED"

    assigned = client.get("/api/collector/assignments", headers=collector_headers)
    assert assigned.status_code == 200, assigned.text
    assert any(item["id"] == pickup_id for item in assigned.json())

    accepted = client.post(f"/api/collector/assignments/{pickup_id}/accept", headers=collector_headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"

    started = client.post(f"/api/collector/assignments/{pickup_id}/start", headers=collector_headers)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "IN_PROGRESS"

    scanned = client.post(
        f"/api/collector/assignments/{pickup_id}/scan",
        json={"token": passport["qr_token"] if "qr_token" in passport else ""},
        headers=collector_headers,
    )
    assert scanned.status_code == 200, scanned.text


def test_handover_requires_confirmation_and_damaged_seal_note(collector_headers, admin_headers, ward_headers):
    passport = _create_passport(ward_headers)
    request_response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport["id"]},
        headers=ward_headers,
    )
    pickup_id = request_response.json()["id"]

    assign = client.post(
        f"/api/pickups/{pickup_id}/assign",
        json={"collector_id": 1},
        headers=admin_headers,
    )
    assert assign.status_code == 200, assign.text

    client.post(f"/api/collector/assignments/{pickup_id}/accept", headers=collector_headers)
    client.post(f"/api/collector/assignments/{pickup_id}/start", headers=collector_headers)
    client.post(
        f"/api/collector/assignments/{pickup_id}/scan",
        json={"token": passport["qr_token"] if "qr_token" in passport else ""},
        headers=collector_headers,
    )

    missing = client.post(
        f"/api/collector/assignments/{pickup_id}/handover",
        json={"seal_condition": "INTACT", "checklist": {"bag_identity_verified": True, "qr_scan_successful": True, "category_verified": True, "seal_condition_verified": True, "weight_verified": True, "ppe_verified": False}},
        headers=collector_headers,
    )
    assert missing.status_code in {400, 422}, missing.text

    damaged = client.post(
        f"/api/collector/assignments/{pickup_id}/handover",
        json={"seal_condition": "DAMAGED", "notes": "Seal torn during collection.", "checklist": {"bag_identity_verified": True, "qr_scan_successful": True, "category_verified": True, "seal_condition_verified": True, "weight_verified": True, "ppe_verified": True}},
        headers=collector_headers,
    )
    assert damaged.status_code == 200, damaged.text
    assert damaged.json()["status"] == "COLLECTED"
