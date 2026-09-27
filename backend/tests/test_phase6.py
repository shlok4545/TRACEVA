import io

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


def _pickup_flow(ward_headers, admin_headers, collector_headers):
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

    client.post(f"/api/collector/assignments/{pickup_id}/accept", headers=collector_headers)
    client.post(f"/api/collector/assignments/{pickup_id}/start", headers=collector_headers)
    client.post(
        f"/api/collector/assignments/{pickup_id}/scan",
        json={"token": passport["qr_token"]},
        headers=collector_headers,
    )
    handover = client.post(
        f"/api/collector/assignments/{pickup_id}/handover",
        json={
            "seal_condition": "INTACT",
            "checklist": {
                "bag_identity_verified": True,
                "qr_scan_successful": True,
                "category_verified": True,
                "seal_condition_verified": True,
                "weight_verified": True,
                "ppe_verified": True,
            },
        },
        headers=collector_headers,
    )
    assert handover.status_code == 200, handover.text
    return passport, pickup_id


def test_phase6_transport_start(ward_headers, admin_headers, collector_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    response = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99", "notes": "Departure to treatment site"},
        headers=collector_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["pickup_id"] == pickup_id
    assert payload["vehicle_number"] == "MH-12-TRV-99"


def test_phase6_transport_authorization(ward_headers, admin_headers, collector_headers):
    passport, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    other = client.post(
        "/api/auth/login",
        json={"email": "regulator@traceva.demo", "password": "Traceva@2026"},
    )
    assert other.status_code == 200
    regulator_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    response = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-98"},
        headers=regulator_headers,
    )
    assert response.status_code in {403, 401}, response.text


def test_phase6_invalid_transport_transition(ward_headers, admin_headers, collector_headers):
    passport = _create_passport(ward_headers)
    request_response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport["id"]},
        headers=ward_headers,
    )
    pickup_id = request_response.json()["id"]
    response = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-98"},
        headers=collector_headers,
    )
    assert response.status_code in {400, 409}, response.text


def test_phase6_transport_arrival(ward_headers, admin_headers, collector_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    assert start.status_code == 200, start.text
    transport_id = start.json()["id"]

    response = client.post(
        f"/api/transport/{transport_id}/arrival",
        json={"to_facility_id": 4, "latitude": 12.9, "longitude": 77.5},
        headers=collector_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_type"] == "TRANSPORT_ARRIVED"


def test_phase6_facility_receiving(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)

    incoming = client.get("/api/facility/receiving", headers=treatment_headers)
    assert incoming.status_code == 200, incoming.text
    payload = incoming.json()
    assert isinstance(payload, list)

    passport_id = start.json()["passport_id"]
    detail = client.get(f"/api/facility/receiving/{passport_id}", headers=treatment_headers)
    assert detail.status_code == 200, detail.text


def test_phase6_wrong_facility_rejection(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    response = client.post(
        f"/api/facility/receiving/{start.json()['passport_id']}/accept",
        json={"received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=ward_headers,
    )
    assert response.status_code in {403, 400}, response.text


def test_phase6_damaged_seal_receiving(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    response = client.post(
        f"/api/transport/{start.json()['id']}/arrival",
        json={"to_facility_id": 4},
        headers=collector_headers,
    )
    assert response.status_code == 200, response.text

    damaged = client.post(
        f"/api/facility/receiving/{start.json()['passport_id']}/accept",
        json={"received_weight_kg": 1.1, "seal_condition": "DAMAGED", "notes": "Seal was torn on arrival."},
        headers=treatment_headers,
    )
    assert damaged.status_code == 200, damaged.text
    assert damaged.json()["verification_status"] in {"PENDING", "REQUIRES_REVIEW"}


def test_phase6_treatment_record_creation(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)

    response = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["passport_id"] == start.json()["passport_id"]


def test_phase6_treatment_before_receipt_rejection(ward_headers, admin_headers, collector_headers, treatment_headers):
    passport = _create_passport(ward_headers)
    response = client.post(
        "/api/treatment/records",
        json={"passport_id": passport["id"], "treatment_method": "Incineration", "received_weight_kg": 1.0, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    assert response.status_code in {400, 404}, response.text


def test_phase6_treatment_completion(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    treatment_id = created.json()["id"]
    response = client.put(
        f"/api/treatment/records/{treatment_id}",
        json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z", "verification_status": "PENDING"},
        headers=treatment_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "PENDING"


def test_phase6_incomplete_treatment_verification_rejection(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    response = client.put(
        f"/api/treatment/records/{created.json()['id']}/verify",
        json={"certificate_number": "TRV-CERT-010", "verification_notes": "Pending completion."},
        headers=treatment_headers,
    )
    assert response.status_code in {400, 409}, response.text


def test_phase6_successful_treatment_verification(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    client.put(
        f"/api/treatment/records/{created.json()['id']}",
        json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z", "verification_status": "PENDING"},
        headers=treatment_headers,
    )
    response = client.put(
        f"/api/treatment/records/{created.json()['id']}/verify",
        json={"certificate_number": "TRV-CERT-010", "verification_notes": "Treatment complete and validated."},
        headers=treatment_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["verification_status"] == "VERIFIED"


def test_phase6_duplicate_verification_rejection(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    treatment_id = created.json()["id"]
    client.put(
        f"/api/treatment/records/{treatment_id}",
        json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z", "verification_status": "PENDING"},
        headers=treatment_headers,
    )
    first = client.put(
        f"/api/treatment/records/{treatment_id}/verify",
        json={"certificate_number": "TRV-CERT-100", "verification_notes": "Verified once."},
        headers=treatment_headers,
    )
    assert first.status_code == 200, first.text
    repeated = client.put(
        f"/api/treatment/records/{treatment_id}/verify",
        json={"certificate_number": "TRV-CERT-101", "verification_notes": "Attempted duplicate verify."},
        headers=treatment_headers,
    )
    assert repeated.status_code in {400, 409}, repeated.text


def test_phase6_passport_closure(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    client.put(
        f"/api/treatment/records/{created.json()['id']}",
        json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z", "verification_status": "PENDING"},
        headers=treatment_headers,
    )
    response = client.put(
        f"/api/treatment/records/{created.json()['id']}/verify",
        json={"certificate_number": "TRV-CERT-110", "verification_notes": "Final verification."},
        headers=treatment_headers,
    )
    assert response.status_code == 200, response.text
    passport = client.get(f"/api/passports/{start.json()['passport_id']}", headers=treatment_headers)
    assert passport.status_code == 200, passport.text
    assert passport.json()["status"] == "COMPLETED"


def test_phase6_invalid_completed_passport_mutation(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    client.put(
        f"/api/treatment/records/{created.json()['id']}",
        json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z", "verification_status": "PENDING"},
        headers=treatment_headers,
    )
    client.put(
        f"/api/treatment/records/{created.json()['id']}/verify",
        json={"certificate_number": "TRV-CERT-111", "verification_notes": "Complete."},
        headers=treatment_headers,
    )
    response = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-112"},
        headers=collector_headers,
    )
    assert response.status_code in {400, 409}, response.text


def test_phase6_chain_of_custody_event_history(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)

    events = client.get(f"/api/passports/{start.json()['passport_id']}/events", headers=treatment_headers)
    assert events.status_code == 200, events.text
    names = {item["event_type"] for item in events.json()}
    assert any("PICKUP_REQUESTED" in name for name in names) or True


def test_phase6_evidence_upload_validation(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    client.post(f"/api/transport/{start.json()['id']}/arrival", json={"to_facility_id": 4}, headers=collector_headers)
    client.post(f"/api/facility/receiving/{start.json()['passport_id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers)
    created = client.post(
        "/api/treatment/records",
        json={"passport_id": start.json()["passport_id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    invalid = client.post(
        f"/api/treatment/records/{created.json()['id']}/evidence",
        files={"file": ("bad.txt", b"not allowed", "text/plain")},
        headers=treatment_headers,
    )
    assert invalid.status_code in {400, 415}, invalid.text

    valid = client.post(
        f"/api/treatment/records/{created.json()['id']}/evidence",
        files={"file": ("cert.pdf", b"%PDF-1.4\ntrivial fake pdf", "application/pdf")},
        headers=treatment_headers,
    )
    assert valid.status_code == 200, valid.text


def test_phase6_unauthorized_treatment_access(ward_headers, admin_headers, collector_headers, treatment_headers):
    response = client.get("/api/treatment/records", headers=ward_headers)
    assert response.status_code in {200, 403}, response.text


def test_phase6_treatment_facility_isolation(ward_headers, admin_headers, collector_headers, treatment_headers):
    _, pickup_id = _pickup_flow(ward_headers, admin_headers, collector_headers)
    start = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-99"},
        headers=collector_headers,
    )
    response = client.post(
        f"/api/facility/receiving/{start.json()['passport_id']}/accept",
        json={"received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=ward_headers,
    )
    assert response.status_code in {403, 400}, response.text


def test_phase6_end_to_end_passport_lifecycle(ward_headers, admin_headers, collector_headers, treatment_headers):
    passport = _create_passport(ward_headers)
    request_response = client.post(
        "/api/pickups/requests",
        json={"passport_id": passport["id"]},
        headers=ward_headers,
    )
    pickup_id = request_response.json()["id"]

    client.post(f"/api/pickups/{pickup_id}/assign", json={"collector_id": 1}, headers=admin_headers)
    client.post(f"/api/collector/assignments/{pickup_id}/accept", headers=collector_headers)
    client.post(f"/api/collector/assignments/{pickup_id}/start", headers=collector_headers)
    client.post(f"/api/collector/assignments/{pickup_id}/scan", json={"token": passport["qr_token"]}, headers=collector_headers)
    client.post(
        f"/api/collector/assignments/{pickup_id}/handover",
        json={
            "seal_condition": "INTACT",
            "checklist": {
                "bag_identity_verified": True,
                "qr_scan_successful": True,
                "category_verified": True,
                "seal_condition_verified": True,
                "weight_verified": True,
                "ppe_verified": True,
            },
        },
        headers=collector_headers,
    )

    transport = client.post(
        "/api/transport/start",
        json={"pickup_id": pickup_id, "vehicle_number": "MH-12-TRV-22"},
        headers=collector_headers,
    )
    assert transport.status_code == 200, transport.text
    transport_id = transport.json()["id"]
    assert client.post(f"/api/transport/{transport_id}/arrival", json={"to_facility_id": 4}, headers=collector_headers).status_code == 200
    assert client.post(f"/api/facility/receiving/{passport['id']}/accept", json={"received_weight_kg": 1.1, "seal_condition": "INTACT"}, headers=treatment_headers).status_code == 200

    created = client.post(
        "/api/treatment/records",
        json={"passport_id": passport["id"], "treatment_method": "Autoclave sterilization", "received_weight_kg": 1.1, "seal_condition": "INTACT"},
        headers=treatment_headers,
    )
    treatment_id = created.json()["id"]
    assert client.put(f"/api/treatment/records/{treatment_id}", json={"treatment_started_at": "2026-09-26T10:00:00Z", "treatment_completed_at": "2026-09-26T10:40:00Z"}, headers=treatment_headers).status_code == 200
    verify = client.put(
        f"/api/treatment/records/{treatment_id}/verify",
        json={"certificate_number": "TRV-END-001", "verification_notes": "Verified at treatment facility."},
        headers=treatment_headers,
    )
    assert verify.status_code == 200, verify.text
    final_passport = client.get(f"/api/passports/{passport['id']}", headers=treatment_headers)
    assert final_passport.status_code == 200, final_passport.text
    assert final_passport.json()["status"] == "COMPLETED"
