from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.facility import Facility
from app.models.pickup import PickupRequest
from app.models.transport import TransportEvent
from app.models.user import User
from app.models.waste import WastePassport, WastePassportEvent

router = APIRouter()

VALID_TRANSPORT_EVENT_TYPES = {"TRANSPORT_STARTED", "TRANSPORT_ARRIVED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_collector(current_user: User) -> None:
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only collectors can manage transport execution.")


def _get_transport_or_404(db: Session, transport_id: int) -> TransportEvent:
    item = db.query(TransportEvent).filter(TransportEvent.id == transport_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport record not found.")
    return item


@router.post("/start")
async def start_transport(
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_collector(current_user)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transport details are required.")
    pickup_id = int(payload.get("pickup_id"))
    request = db.query(PickupRequest).filter(PickupRequest.id == pickup_id).first()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup request not found.")
    if request.assigned_collector_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This pickup has not been assigned to a collector.")
    if request.passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found for this pickup.")
    if request.passport.status in {"COMPLETED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This passport is no longer eligible for transport.")
    if request.status not in {"COLLECTED", "IN_PROGRESS", "ACCEPTED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pickup must be collected or in progress before transport starts.")

    profile = current_user.collector_profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collector profile not found.")
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")

    existing = db.query(TransportEvent).filter(TransportEvent.pickup_request_id == pickup_id, TransportEvent.event_type == "TRANSPORT_STARTED").first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transport has already started for this pickup.")

    vehicle_number = str(payload.get("vehicle_number") or "").strip() or profile.vehicle_number or "UNKNOWN"
    event = TransportEvent(
        pickup_request_id=request.id,
        passport_id=request.passport_id,
        collector_id=profile.id,
        event_type="TRANSPORT_STARTED",
        from_facility_id=request.facility_id,
        to_facility_id=payload.get("to_facility_id"),
        vehicle_number=vehicle_number,
        departure_time=_utc_now(),
        seal_status=str(payload.get("seal_condition") or "INTACT").upper(),
        notes=payload.get("notes"),
        created_by_user_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    request.passport.status = "IN_TRANSIT"
    request.passport.updated_at = _utc_now()
    db.add(WastePassportEvent(passport_id=request.passport_id, event_type="TRANSPORT_STARTED", details=f"Waste moved in vehicle {vehicle_number}", actor_name=current_user.name))
    db.commit()
    return {
        "id": event.id,
        "pickup_id": request.id,
        "passport_id": request.passport_id,
        "event_type": event.event_type,
        "vehicle_number": event.vehicle_number,
        "from_facility_id": event.from_facility_id,
        "to_facility_id": event.to_facility_id,
        "departure_time": event.departure_time,
        "seal_status": event.seal_status,
        "notes": event.notes,
        "created_at": event.created_at,
    }


@router.get("/{transport_id}")
async def get_transport_record(
    transport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = _get_transport_or_404(db, transport_id)
    if current_user.role not in {"ADMIN", "REGULATOR", "COLLECTOR"} and current_user.facility_id != event.from_facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this transport record.")
    return {
        "id": event.id,
        "pickup_id": event.pickup_request_id,
        "passport_id": event.passport_id,
        "event_type": event.event_type,
        "from_facility_id": event.from_facility_id,
        "to_facility_id": event.to_facility_id,
        "vehicle_number": event.vehicle_number,
        "arrival_time": event.arrival_time,
        "departure_time": event.departure_time,
        "seal_status": event.seal_status,
        "notes": event.notes,
        "created_at": event.created_at,
    }


@router.post("/{transport_id}/arrival")
async def mark_transport_arrival(
    transport_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_collector(current_user)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arrival details are required.")
    event = _get_transport_or_404(db, transport_id)
    if event.event_type != "TRANSPORT_STARTED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transport must start before arrival can be recorded.")
    if current_user.collector_profile is None or event.collector_id != current_user.collector_profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This transport event belongs to another collector.")

    to_facility_id = int(payload.get("to_facility_id") or 0)
    facility = db.query(Facility).filter(Facility.id == to_facility_id).first()
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination facility not found.")
    if to_facility_id != 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only the designated treatment facility is valid for final handoff.")

    event.to_facility_id = to_facility_id
    event.event_type = "TRANSPORT_ARRIVED"
    event.arrival_time = _utc_now()
    event.latitude = payload.get("latitude")
    event.longitude = payload.get("longitude")
    event.notes = (payload.get("notes") or event.notes)
    event.created_by_user_id = current_user.id
    db.commit()
    db.refresh(event)

    passport = db.query(WastePassport).filter(WastePassport.id == event.passport_id).first()
    if passport is not None:
        passport.status = "AT_TREATMENT"
        passport.updated_at = _utc_now()
        db.add(WastePassportEvent(passport_id=passport.id, event_type="TRANSPORT_ARRIVED", details=f"Waste arrived at treatment facility {facility.name}", actor_name=current_user.name))
    db.commit()
    return {
        "id": event.id,
        "pickup_id": event.pickup_request_id,
        "passport_id": event.passport_id,
        "event_type": event.event_type,
        "to_facility_id": event.to_facility_id,
        "arrival_time": event.arrival_time,
        "vehicle_number": event.vehicle_number,
    }
