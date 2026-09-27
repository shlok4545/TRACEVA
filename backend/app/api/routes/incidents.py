from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.incident import Incident
from app.models.user import User
from app.services.incident_service import apply_facility_scope, assign_incident, acknowledge_incident, close_incident, create_incident, resolve_incident, serialize_incident, VALID_INCIDENT_TYPES, VALID_SEVERITIES, VALID_STATUSES

router = APIRouter()


@router.post("")
async def create_incident_endpoint(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return serialize_incident(create_incident(db, current_user, payload), db)


@router.get("")
async def list_incidents(
    facility: int | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    incident_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    passport_number: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Incident)
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(Incident.facility_id == (current_user.facility_id or -1))
    if facility is not None:
        if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != facility:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view that facility's incidents.")
        query = query.filter(Incident.facility_id == facility)
    if severity:
        query = query.filter(Incident.severity == severity.upper())
    if status:
        query = query.filter(Incident.status == status.upper())
    if incident_type:
        query = query.filter(Incident.incident_type == incident_type.upper())
    if passport_number:
        query = query.filter(Incident.passport_id.in_([i.id for i in db.query(Incident.passport_id).all() if i[0] is not None]))
    query = query.order_by(Incident.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"items": [serialize_incident(item, db) for item in items], "page": page, "limit": limit, "total": total}


@router.get("/{incident_id}")
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    return serialize_incident(incident, db)


@router.put("/{incident_id}")
async def update_incident(
    incident_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    if "severity" in payload:
        severity = str(payload["severity"]).upper()
        if severity not in VALID_SEVERITIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="severity must be one of LOW, MEDIUM, HIGH, CRITICAL.")
        incident.severity = severity
    if "status" in payload:
        status_value = str(payload["status"]).upper()
        if status_value not in VALID_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be one of OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, CLOSED.")
        incident.status = status_value
    if "title" in payload:
        incident.title = str(payload["title"]).strip() or incident.title
    if "description" in payload:
        incident.description = str(payload["description"]) or incident.description
    incident.updated_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.commit()
    db.refresh(incident)
    return serialize_incident(incident, db)


@router.post("/{incident_id}/acknowledge")
async def acknowledge_incident_endpoint(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    return serialize_incident(acknowledge_incident(db, incident, current_user), db)


@router.post("/{incident_id}/assign")
async def assign_incident_endpoint(
    incident_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    assigned = payload.get("assigned_to_user_id") if payload else None
    return serialize_incident(assign_incident(db, incident, assigned, current_user), db)


@router.post("/{incident_id}/resolve")
async def resolve_incident_endpoint(
    incident_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    return serialize_incident(resolve_incident(db, incident, payload or {}, current_user), db)


@router.post("/{incident_id}/close")
async def close_incident_endpoint(
    incident_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != incident.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Incident not available in your facility scope.")
    return serialize_incident(close_incident(db, incident, payload or {}, current_user), db)
