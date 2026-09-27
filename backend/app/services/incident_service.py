from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.incident import Incident
from app.models.pickup import Notification, PickupRequest
from app.models.user import User
from app.models.waste import WastePassport

VALID_INCIDENT_TYPES = {
    "WRONG_SEGREGATION",
    "DAMAGED_SEAL",
    "LEAKAGE",
    "PICKUP_DELAY",
    "MISSED_PICKUP",
    "QR_VALIDATION_FAILURE",
    "FACILITY_MISMATCH",
    "TREATMENT_DELAY",
    "MISSING_TREATMENT_VERIFICATION",
    "CHAIN_OF_CUSTODY_GAP",
    "OTHER",
}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_STATUSES = {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "CLOSED"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def user_cannot_access_facility(user: User, facility_id: int | None) -> bool:
    if user.role == "ADMIN" or user.role == "REGULATOR":
        return False
    return facility_id is None or user.facility_id != facility_id


def apply_facility_scope(db: Session, user: User, query):
    if user.role in {"ADMIN", "REGULATOR"}:
        return query
    if user.facility_id is None:
        return query.filter(False)
    return query.filter(Incident.facility_id == user.facility_id)


def serialize_incident(incident: Incident, db: Session) -> dict[str, Any]:
    facility = db.query(Facility).filter(Facility.id == incident.facility_id).first()
    passport = db.query(WastePassport).filter(WastePassport.id == incident.passport_id).first() if incident.passport_id else None
    reported_by = db.query(User).filter(User.id == incident.reported_by_user_id).first()
    assigned_to = db.query(User).filter(User.id == incident.assigned_to_user_id).first() if incident.assigned_to_user_id else None
    return {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "facility_id": incident.facility_id,
        "facility_name": facility.name if facility else None,
        "passport_id": incident.passport_id,
        "passport_number": passport.passport_number if passport else None,
        "pickup_request_id": incident.pickup_request_id,
        "reported_by_user_id": incident.reported_by_user_id,
        "reported_by_name": reported_by.name if reported_by else None,
        "assigned_to_user_id": incident.assigned_to_user_id,
        "assigned_to_name": assigned_to.name if assigned_to else None,
        "incident_type": incident.incident_type,
        "severity": incident.severity,
        "title": incident.title,
        "description": incident.description,
        "status": incident.status,
        "detected_at": incident.detected_at,
        "acknowledged_at": incident.acknowledged_at,
        "resolved_at": incident.resolved_at,
        "resolution_notes": incident.resolution_notes,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
    }


def create_or_update_notification(db: Session, user_id: int | None, notification_type: str, title: str, message: str, severity: str | None = None) -> Notification:
    existing = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.notification_type == notification_type,
        Notification.title == title,
        Notification.message == message,
    ).first()
    if existing is not None:
        return existing
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=(severity or "INFO").upper(),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_incident(db: Session, current_user: User, payload: dict[str, Any]) -> Incident:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident payload is required.")

    facility_id = int(payload.get("facility_id") or current_user.facility_id or 0)
    if facility_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="facility_id is required.")
    if user_cannot_access_facility(current_user, facility_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot report incidents for this facility.")

    incident_type = str(payload.get("incident_type") or "").upper()
    if incident_type not in VALID_INCIDENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported incident_type. Allowed: {sorted(VALID_INCIDENT_TYPES)}")
    severity = str(payload.get("severity") or "MEDIUM").upper()
    if severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="severity must be one of LOW, MEDIUM, HIGH, CRITICAL.")

    title = str(payload.get("title") or "Operational incident").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title is required.")

    incident = Incident(
        facility_id=facility_id,
        passport_id=int(payload["passport_id"]) if payload.get("passport_id") not in (None, "") else None,
        pickup_request_id=int(payload["pickup_request_id"]) if payload.get("pickup_request_id") not in (None, "") else None,
        reported_by_user_id=current_user.id,
        assigned_to_user_id=payload.get("assigned_to_user_id"),
        incident_type=incident_type,
        severity=severity,
        title=title,
        description=str(payload.get("description") or ""),
        status="OPEN",
        detected_at=_iso(_utc_now()),
    )
    max_id = db.query(Incident.id).order_by(Incident.id.desc()).first()
    next_id = (max_id[0] if max_id else 0) + 1
    incident.incident_number = f"INC-{next_id:04d}"
    db.add(incident)
    db.commit()
    db.refresh(incident)
    create_or_update_notification(
        db,
        current_user.id,
        "incident_created",
        "Incident recorded",
        f"Incident {incident.incident_number} has been created for {incident.title}.",
    )
    return incident


def acknowledge_incident(db: Session, incident: Incident, current_user: User) -> Incident:
    if incident.status == "CLOSED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Closed incidents cannot be acknowledged.")
    incident.status = "ACKNOWLEDGED"
    incident.acknowledged_at = _iso(_utc_now())
    incident.updated_at = _iso(_utc_now())
    db.commit()
    return incident


def assign_incident(db: Session, incident: Incident, user_id: int | None, current_user: User) -> Incident:
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assigned_to_user_id is required.")
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found.")
    incident.assigned_to_user_id = user_id
    incident.status = "IN_PROGRESS" if incident.status in {"OPEN", "ACKNOWLEDGED"} else incident.status
    incident.updated_at = _iso(_utc_now())
    db.commit()
    return incident


def resolve_incident(db: Session, incident: Incident, payload: dict[str, Any], current_user: User) -> Incident:
    notes = (payload or {}).get("resolution_notes") or "Resolved by operations team."
    incident.status = "RESOLVED"
    incident.resolved_at = _iso(_utc_now())
    incident.resolution_notes = str(notes)
    incident.updated_at = _iso(_utc_now())
    db.commit()
    return incident


def close_incident(db: Session, incident: Incident, payload: dict[str, Any], current_user: User) -> Incident:
    if incident.status not in {"RESOLVED", "CLOSED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only resolved incidents can be closed.")
    incident.status = "CLOSED"
    incident.updated_at = _iso(_utc_now())
    if payload and payload.get("resolution_notes"):
        incident.resolution_notes = str(payload.get("resolution_notes"))
    db.commit()
    return incident


def build_alerts(db: Session, user: User | None = None) -> list[dict[str, Any]]:
    debt = []
    query = db.query(PickupRequest)
    if user is not None and user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(PickupRequest.facility_id == (user.facility_id or -1))
    overdue_pickups = query.filter(PickupRequest.status.notin_({"COLLECTED", "CANCELLED"}), PickupRequest.due_at.isnot(None)).all()
    now = _utc_now()
    for pickup in overdue_pickups:
        if pickup.due_at:
            due_at = _parse_iso(pickup.due_at)
            if due_at and due_at < now:
                debt.append({
                    "key": f"pickup_overdue:{pickup.id}",
                    "severity": "HIGH",
                    "title": "Pickup overdue",
                    "message": f"Pickup for passport {pickup.passport_id} is overdue.",
                    "entity": "pickup",
                    "entity_id": pickup.id,
                })

    treatment_records = db.query(__import__('app.models.transport', fromlist=['TreatmentRecord']).TreatmentRecord).all()
    for record in treatment_records:
        if record.verification_status == "PENDING":
            debt.append({
                "key": f"treatment_pending:{record.id}",
                "severity": "MEDIUM",
                "title": "Treatment verification pending",
                "message": f"Treatment record {record.id} is awaiting verification.",
                "entity": "treatment_record",
                "entity_id": record.id,
            })

    incidents = db.query(Incident).all()
    for item in incidents:
        if item.severity in {"HIGH", "CRITICAL"} and item.status in {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS"}:
            debt.append({
                "key": f"incident_alert:{item.id}",
                "severity": item.severity,
                "title": item.title,
                "message": item.description or "Open high-priority operational incident.",
                "entity": "incident",
                "entity_id": item.id,
            })
    unique = {}
    for item in debt:
        unique[item["key"]] = item
    ordered = sorted(unique.values(), key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x["severity"], 9))
    return ordered[:20]
