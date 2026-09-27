from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.facility import Facility
from app.models.pickup import CollectorProfile, Notification, PickupEvent, PickupRequest
from app.models.user import User
from app.models.ward import Ward
from app.models.waste import WastePassport, WastePassportEvent

router = APIRouter()

VALID_PICKUP_STATUSES = {"REQUESTED", "QUEUED", "ASSIGNED", "ACCEPTED", "IN_PROGRESS", "COLLECTED", "CANCELLED"}
TERMINAL_PICKUP_STATUSES = {"COLLECTED", "CANCELLED"}
PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
VALID_SEAL_CONDITIONS = {"INTACT", "DAMAGED", "LEAKING", "UNKNOWN"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _priority_from_risk_score(score: float | None) -> str:
    if score is None:
        return "MEDIUM"
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _make_due_at(priority: str) -> str:
    now = _utc_now()
    hours = {"CRITICAL": 2, "HIGH": 4, "MEDIUM": 8, "LOW": 12}.get(priority, 8)
    return _iso(now + timedelta(hours=hours))


def _add_notification(db: Session, user_id: int | None, notification_type: str, title: str, message: str) -> None:
    db.add(Notification(user_id=user_id, notification_type=notification_type, title=title, message=message))


def _add_pickup_event(
    db: Session,
    pickup_request: PickupRequest,
    event_type: str,
    actor_user_id: int | None = None,
    collector_id: int | None = None,
    notes: str | None = None,
    verification_method: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> None:
    db.add(
        PickupEvent(
            pickup_request_id=pickup_request.id,
            passport_id=pickup_request.passport_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            collector_id=collector_id,
            notes=notes,
            verification_method=verification_method,
            latitude=latitude,
            longitude=longitude,
        )
    )


def _serialize_pickup_request(request: PickupRequest, db: Session) -> dict[str, Any]:
    passport = request.passport
    facility = db.query(Facility).filter(Facility.id == request.facility_id).first()
    ward = db.query(Ward).filter(Ward.id == passport.ward_id).first() if passport and passport.ward_id else None
    current_time = _utc_now()
    created_at = _parse_iso(request.requested_at) or current_time
    waiting_minutes = max(0, int((current_time - created_at).total_seconds() // 60))
    due_at_dt = _parse_iso(request.due_at)
    is_overdue = due_at_dt is not None and current_time > due_at_dt and request.status not in TERMINAL_PICKUP_STATUSES
    return {
        "id": request.id,
        "passport_id": request.passport_id,
        "passport_number": passport.passport_number if passport else None,
        "facility_id": request.facility_id,
        "facility_name": facility.name if facility else None,
        "ward_id": passport.ward_id if passport else None,
        "ward_name": ward.name if ward else None,
        "requested_by_user_id": request.requested_by_user_id,
        "assigned_collector_id": request.assigned_collector_id,
        "assigned_collector_name": request.assigned_collector.user.name if request.assigned_collector and request.assigned_collector.user else None,
        "priority": request.priority,
        "risk_score_snapshot": request.risk_score_snapshot,
        "status": request.status,
        "requested_at": request.requested_at,
        "assigned_at": request.assigned_at,
        "accepted_at": request.accepted_at,
        "pickup_started_at": request.pickup_started_at,
        "completed_at": request.completed_at,
        "due_at": request.due_at,
        "notes": request.notes,
        "waiting_minutes": waiting_minutes,
        "waiting_hours": round(waiting_minutes / 60, 2),
        "is_overdue": is_overdue,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
    }


def _permission_for_pickup(current_user: User, facility_id: int) -> None:
    if current_user.role == "ADMIN":
        return
    if current_user.role == "REGULATOR":
        return
    if current_user.facility_id != facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage pickups in your facility.")


def _collector_profile_for_user(db: Session, current_user: User) -> CollectorProfile:
    profile = db.query(CollectorProfile).filter(CollectorProfile.user_id == current_user.id).first()
    if profile is None:
        if current_user.role != "COLLECTOR":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This action is only available to collectors.")
        profile = CollectorProfile(
            user_id=current_user.id,
            facility_id=current_user.facility_id or 1,
            employee_code=f"COL-{current_user.id:03d}",
            phone=None,
            availability_status="AVAILABLE",
            active=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _get_pickup_request_or_404(db: Session, pickup_id: int) -> PickupRequest:
    request = db.query(PickupRequest).filter(PickupRequest.id == pickup_id).first()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pickup request not found.")
    return request


@router.get("")
async def list_pickups_root() -> dict[str, Any]:
    return {"message": "TRACEVA pickup service", "status": "online"}


@router.post("/requests")
async def create_pickup_request(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload or "passport_id" not in payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="passport_id is required.")

    passport = db.query(WastePassport).filter(WastePassport.id == int(payload["passport_id"])).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    if current_user.role not in {"WARD_STAFF", "ADMIN", "REGULATOR"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only ward staff or admin can request a pickup.")
    if current_user.role != "ADMIN" and current_user.facility_id != passport.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This passport belongs to a different facility.")
    if passport.status in {"COMPLETED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This passport is not eligible for a new pickup request.")
    if db.query(PickupRequest).filter(PickupRequest.passport_id == passport.id, PickupRequest.status.notin_(TERMINAL_PICKUP_STATUSES)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active pickup request already exists for this passport.")
    risk_score = max((float(item.risk_score) for item in passport.items if item.risk_score is not None), default=0.0)
    priority = passport.risk_priority or _priority_from_risk_score(risk_score)
    request = PickupRequest(
        passport_id=passport.id,
        facility_id=passport.facility_id,
        requested_by_user_id=current_user.id,
        priority=priority,
        risk_score_snapshot=risk_score,
        status="QUEUED",
        due_at=_make_due_at(priority),
        notes=payload.get("notes"),
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    passport.status = "READY_FOR_PICKUP"
    passport.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "PICKUP_REQUESTED", actor_user_id=current_user.id, notes="Pickup requested by ward staff.")
    _add_notification(db, None, "pickup_requested", "Pickup requested", f"Pickup requested for passport {passport.passport_number}.")
    for admin in db.query(User).filter(User.role == "ADMIN").all():
        _add_notification(db, admin.id, "pickup_requested", "Pickup requested", f"Passport {passport.passport_number} is waiting for assignment.")
    db.add(WastePassportEvent(passport_id=passport.id, event_type="PICKUP_REQUESTED", details="Pickup requested", actor_name=current_user.name))
    db.commit()
    return _serialize_pickup_request(request, db)


@router.get("/requests")
async def list_pickup_requests(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    facility: int | None = Query(default=None),
    collector: int | None = Query(default=None),
    date: str | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PickupRequest)
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(PickupRequest.facility_id == current_user.facility_id)
    if status:
        query = query.filter(PickupRequest.status == status.upper())
    if priority:
        query = query.filter(PickupRequest.priority == priority.upper())
    if facility is not None:
        query = query.filter(PickupRequest.facility_id == facility)
    if collector is not None:
        query = query.filter(PickupRequest.assigned_collector_id == collector)
    if date:
        target = date
        query = query.filter(PickupRequest.requested_at.like(f"{target}%"))
    if search:
        like = f"%{search}%"
        query = query.join(WastePassport).filter(WastePassport.passport_number.like(like))

    requests = query.order_by(PickupRequest.priority.asc(), PickupRequest.requested_at.asc()).all()
    return [_serialize_pickup_request(req, db) for req in requests]


@router.get("/queue")
async def get_pickup_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "REGULATOR", "WARD_STAFF"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to the pickup queue.")
    query = db.query(PickupRequest)
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(PickupRequest.facility_id == current_user.facility_id)
    queue = query.order_by(PickupRequest.priority.asc(), PickupRequest.requested_at.asc()).all()
    items = []
    for request in queue:
        passport = request.passport
        if passport is None:
            continue
        ward = db.query(Ward).filter(Ward.id == passport.ward_id).first() if passport.ward_id else None
        collector = request.assigned_collector.user if request.assigned_collector else None
        due = _parse_iso(request.due_at)
        requested = _parse_iso(request.requested_at) or _utc_now()
        waiting = max(0, int((_utc_now() - requested).total_seconds() // 60))
        item = {
            "id": request.id,
            "passport_number": passport.passport_number,
            "ward": ward.name if ward else None,
            "category": next((item.category for item in passport.items if item.category), "General Biomedical Waste"),
            "risk_score": request.risk_score_snapshot,
            "priority": request.priority,
            "waiting_minutes": waiting,
            "waiting_hours": round(waiting / 60, 2),
            "due_time": request.due_at,
            "status": request.status,
            "assigned_collector": collector.name if collector else None,
            "urgency_explanation": f"{request.priority} priority pickup awaiting collection.",
            "is_overdue": due is not None and _utc_now() > due and request.status not in TERMINAL_PICKUP_STATUSES,
        }
        items.append(item)
    return sorted(items, key=lambda item: (PRIORITY_ORDER.get(item["priority"], 99), item["waiting_minutes"], item["due_time"] or ""))


@router.post("/{pickup_id}/assign")
async def assign_collector(
    pickup_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"ADMIN", "WARD_STAFF"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin or ward staff may assign collectors.")
    request = _get_pickup_request_or_404(db, pickup_id)
    _permission_for_pickup(current_user, request.facility_id)
    collector_id = payload.get("collector_id")
    collector = db.query(CollectorProfile).filter(CollectorProfile.id == int(collector_id)).first() if collector_id is not None else None
    if collector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collector not found.")
    if collector.facility_id != request.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collector is not scoped to this facility.")
    if not collector.active or collector.availability_status != "AVAILABLE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Collector is unavailable for assignment.")
    request.assigned_collector_id = collector.id
    request.assigned_at = _iso(_utc_now())
    request.status = "ASSIGNED"
    request.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "COLLECTOR_ASSIGNED", actor_user_id=current_user.id, collector_id=collector.id, notes="Collector assigned by dispatcher.")
    _add_notification(db, collector.user_id, "collector_assigned", "Collector assigned", f"You have been assigned to pickup passport {request.passport.passport_number}.")
    db.commit()
    return _serialize_pickup_request(request, db)


@router.get("/profile")
async def get_collector_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This endpoint is for collectors only.")
    profile = _collector_profile_for_user(db, current_user)
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "facility_id": profile.facility_id,
        "employee_code": profile.employee_code,
        "vehicle_number": profile.vehicle_number,
        "phone": profile.phone,
        "availability_status": profile.availability_status,
        "current_latitude": profile.current_latitude,
        "current_longitude": profile.current_longitude,
        "last_location_update": profile.last_location_update,
        "active": profile.active,
    }


@router.get("/assignments")
async def list_collector_assignments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    requests = db.query(PickupRequest).filter(PickupRequest.assigned_collector_id == profile.id).order_by(PickupRequest.requested_at.desc()).all()
    return [_serialize_pickup_request(req, db) for req in requests]


@router.get("/assignments/{pickup_id}")
async def get_collector_assignment(pickup_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    return _serialize_pickup_request(request, db)


@router.post("/assignments/{pickup_id}/accept")
async def accept_assignment(pickup_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    if request.status not in {"ASSIGNED", "QUEUED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This pickup cannot be accepted in its current state.")
    request.status = "ACCEPTED"
    request.accepted_at = _iso(_utc_now())
    request.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "COLLECTOR_ACCEPTED", actor_user_id=current_user.id, collector_id=profile.id, notes="Collector accepted the assignment.")
    _add_notification(db, current_user.id, "collector_assignment_accepted", "Assignment accepted", f"You accepted pickup {request.passport.passport_number}.")
    db.commit()
    return _serialize_pickup_request(request, db)


@router.post("/assignments/{pickup_id}/start")
async def start_assignment(pickup_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    if request.status not in {"ACCEPTED", "ASSIGNED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pickup must be accepted before starting.")
    request.status = "IN_PROGRESS"
    request.pickup_started_at = _iso(_utc_now())
    request.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "PICKUP_STARTED", actor_user_id=current_user.id, collector_id=profile.id, notes="Collector started pickup collection.")
    db.commit()
    return _serialize_pickup_request(request, db)


@router.post("/assignments/{pickup_id}/scan")
async def scan_assignment_qr(
    pickup_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    if request.status in {"COLLECTED", "CANCELLED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This pickup is already completed or cancelled.")

    token = str((payload or {}).get("token") or "").strip()
    passport = request.passport
    if token:
        validated = db.query(WastePassport).filter(WastePassport.qr_token == token).first()
        if validated is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid QR token.")
        if validated.id != request.passport_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR data does not match the assigned passport.")
        passport = validated
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    if passport.status in {"COMPLETED", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This passport is no longer eligible for collection.")
    request.status = "IN_PROGRESS"
    _add_pickup_event(db, request, "QR_SCANNED", actor_user_id=current_user.id, collector_id=profile.id, notes="QR or manual verification completed.", verification_method="QR" if token else "MANUAL")
    db.commit()
    return {"passport_number": passport.passport_number, "status": request.status, "verified": True}


@router.post("/assignments/{pickup_id}/handover")
async def confirm_handover(
    pickup_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    if request.status in {"COLLECTED", "CANCELLED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This pickup has already been completed.")

    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Handover confirmation details are required.")
    checklist = payload.get("checklist") or {}
    required = {"bag_identity_verified", "qr_scan_successful", "category_verified", "seal_condition_verified", "weight_verified", "ppe_verified"}
    missing = [key for key in required if not bool(checklist.get(key))]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing mandatory checklist items: {', '.join(sorted(missing))}.")

    seal_condition = str(payload.get("seal_condition") or "INTACT").upper()
    if seal_condition not in VALID_SEAL_CONDITIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="seal_condition must be one of INTACT, DAMAGED, LEAKING, UNKNOWN.")
    if seal_condition in {"DAMAGED", "LEAKING"}:
        if not str(payload.get("notes") or "").strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A note is required when seal condition is damaged or leaking.")
        _add_notification(db, request.requested_by_user_id, "damaged_seal_warning", "Damaged seal warning", f"Seal condition for passport {request.passport.passport_number} is {seal_condition}.")

    request.notes = payload.get("notes") or request.notes
    request.status = "COLLECTED"
    request.completed_at = _iso(_utc_now())
    request.updated_at = _iso(_utc_now())
    request.passport.status = "READY_FOR_PICKUP"
    request.passport.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "HANDOVER_VERIFIED", actor_user_id=current_user.id, collector_id=profile.id, notes=f"Handover confirmed. Seal condition: {seal_condition}")
    db.add(WastePassportEvent(passport_id=request.passport_id, event_type="HANDOVER_VERIFIED", details=f"Handover confirmed with seal condition {seal_condition}", actor_name=current_user.name))
    db.commit()
    return _serialize_pickup_request(request, db)


@router.post("/assignments/{pickup_id}/complete")
async def complete_assignment(pickup_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "COLLECTOR":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collectors can only access their assignments.")
    profile = _collector_profile_for_user(db, current_user)
    request = _get_pickup_request_or_404(db, pickup_id)
    if request.assigned_collector_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assignment belongs to another collector.")
    if request.status != "COLLECTED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only collected pickups can be completed.")
    request.completed_at = _iso(_utc_now())
    request.updated_at = _iso(_utc_now())
    _add_pickup_event(db, request, "PICKUP_COMPLETED", actor_user_id=current_user.id, collector_id=profile.id, notes="Pickup completed.")
    _add_notification(db, current_user.id, "pickup_completed", "Pickup complete", f"Pickup {request.passport.passport_number} was completed successfully.")
    db.commit()
    return _serialize_pickup_request(request, db)
