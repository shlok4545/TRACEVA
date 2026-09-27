import base64
import secrets
import struct
import zlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.facility import Facility
from app.models.user import User
from app.models.ward import Ward
from app.models.waste import WastePassport, WastePassportEvent, WastePassportItem
from app.services.risk_service import assess_risk
from app.services.segregation_service import classify_waste

router = APIRouter()
qr_router = APIRouter()

VALID_STATUSES = {"DRAFT", "CLASSIFIED", "READY_FOR_PICKUP", "IN_TRANSIT", "AT_TREATMENT", "COMPLETED", "REJECTED"}
ALLOWED_STATUS_TRANSITIONS = {
    "DRAFT": {"CLASSIFIED"},
    "CLASSIFIED": {"READY_FOR_PICKUP", "REJECTED"},
    "READY_FOR_PICKUP": {"IN_TRANSIT", "REJECTED"},
    "IN_TRANSIT": {"AT_TREATMENT", "REJECTED"},
    "AT_TREATMENT": {"COMPLETED", "REJECTED"},
    "REJECTED": set(),
    "COMPLETED": set(),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _priority_for_score(score: float) -> str:
    if score >= 100:
        return "CRITICAL"
    if score >= 79:
        return "HIGH"
    if score >= 59:
        return "MEDIUM"
    return "LOW"


def _serialize_item(item: WastePassportItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "passport_id": item.passport_id,
        "item_name": item.item_name,
        "item_description": item.item_description,
        "source_department": item.source_department,
        "contamination_level": item.contamination_level,
        "condition": item.condition,
        "quantity": item.quantity,
        "weight_kg": item.weight_kg,
        "category": item.category,
        "segregation_group": item.segregation_group,
        "classification_confidence": item.classification_confidence,
        "requires_human_confirmation": item.requires_human_confirmation,
        "classification_guidance": item.classification_guidance,
        "classification_warning": item.classification_warning,
        "risk_score": item.risk_score,
        "risk_priority": item.risk_priority,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _serialize_passport(passport: WastePassport, db: Session) -> dict[str, Any]:
    facility = db.query(Facility).filter(Facility.id == passport.facility_id).first()
    ward = db.query(Ward).filter(Ward.id == passport.ward_id).first() if passport.ward_id else None
    return {
        "id": passport.id,
        "facility_id": passport.facility_id,
        "facility_name": facility.name if facility else None,
        "ward_id": passport.ward_id,
        "ward_name": ward.name if ward else None,
        "passport_number": passport.passport_number,
        "generated_by_user_id": passport.generated_by_user_id,
        "status": passport.status,
        "risk_priority": passport.risk_priority,
        "total_quantity": passport.total_quantity,
        "total_weight_kg": passport.total_weight_kg,
        "qr_token": passport.qr_token,
        "qr_generated_at": passport.qr_generated_at,
        "created_at": passport.created_at,
        "updated_at": passport.updated_at,
        "items": [_serialize_item(item) for item in sorted(passport.items, key=lambda item: item.id)],
    }


def _generate_passport_number(db: Session) -> str:
    while True:
        suffix = secrets.token_hex(3).upper()
        value = f"TRV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{suffix}"
        if db.query(WastePassport).filter(WastePassport.passport_number == value).first() is None:
            return value


def _add_event(db: Session, passport: WastePassport, event_type: str, details: str, actor_name: str | None = None) -> None:
    db.add(WastePassportEvent(passport_id=passport.id, event_type=event_type, details=details, actor_name=actor_name))
    db.commit()


def _minimal_png() -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return struct.pack("!I", len(payload)) + chunk_type + payload + struct.pack("!I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)

    raw = b"\x00\x00\x00\x00"
    compressed = zlib.compress(raw)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def _generate_qr_data_url() -> str:
    img = _minimal_png()
    return "data:image/png;base64," + base64.b64encode(img).decode("ascii")


def _ensure_facility_access(current_user: User, facility_id: int) -> None:
    if current_user.role in {"ADMIN", "REGULATOR", "TREATMENT_FACILITY"}:
        return
    if current_user.facility_id != facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only access records for your own facility.")


@router.get("")
async def list_passports(
    status: str | None = Query(default=None),
    risk_priority: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(WastePassport)
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(WastePassport.facility_id == current_user.facility_id)
    if status:
        query = query.filter(WastePassport.status == status.upper())
    if risk_priority:
        query = query.filter(WastePassport.risk_priority == risk_priority.upper())
    passports = query.order_by(WastePassport.created_at.desc()).all()
    return [_serialize_passport(passport, db) for passport in passports]


@router.get("/{passport_id}")
async def get_passport(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)
    return _serialize_passport(passport, db)


@router.post("")
async def create_passport(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload or not isinstance(payload.get("items"), list) or not payload["items"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one waste item is required.")

    facility_id = int(payload.get("facility_id") or current_user.facility_id)
    ward_id = payload.get("ward_id")
    if ward_id is not None:
        ward = db.query(Ward).filter(Ward.id == ward_id, Ward.facility_id == facility_id).first()
        if ward is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ward not found for the selected facility.")
    _ensure_facility_access(current_user, facility_id)

    passport = WastePassport(
        facility_id=facility_id,
        ward_id=ward_id,
        passport_number=_generate_passport_number(db),
        generated_by_user_id=current_user.id,
        status="DRAFT",
        risk_priority="LOW",
        total_quantity=0.0,
        total_weight_kg=0.0,
    )
    db.add(passport)
    db.commit()
    db.refresh(passport)

    total_quantity = 0.0
    total_weight = 0.0
    for item_payload in payload["items"]:
        item_name = str(item_payload.get("item_name") or "").strip()
        if not item_name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each item must include an item_name.")
        quantity = float(item_payload.get("quantity") or 0)
        weight_kg = float(item_payload.get("weight_kg") or 0)
        total_quantity += quantity
        total_weight += weight_kg

        item = WastePassportItem(
            passport_id=passport.id,
            item_name=item_name,
            item_description=item_payload.get("item_description"),
            source_department=item_payload.get("source_department"),
            contamination_level=item_payload.get("contamination_level"),
            condition=item_payload.get("condition"),
            quantity=quantity,
            weight_kg=weight_kg,
        )
        db.add(item)

    passport.total_quantity = total_quantity
    passport.total_weight_kg = total_weight
    _add_event(db, passport, "CREATED", f"Waste passport created by {current_user.name}", current_user.name)
    db.commit()
    db.refresh(passport)
    return _serialize_passport(passport, db)


@router.post("/{passport_id}/classify")
async def classify_passport(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)

    classified_items: list[dict[str, Any]] = []
    for item in passport.items:
        result = classify_waste(
            db,
            {
                "item_name": item.item_name,
                "item_description": item.item_description or "",
                "source_department": item.source_department or "",
                "contamination_indication": item.contamination_level or "",
                "condition": item.condition or "",
                "quantity": item.quantity,
            },
        )
        item.category = result.get("category")
        item.segregation_group = result.get("segregation_group")
        item.classification_confidence = result.get("confidence")
        item.requires_human_confirmation = bool(result.get("requires_human_confirmation"))
        item.classification_guidance = result.get("guidance")
        item.classification_warning = result.get("warning")

        risk_result = assess_risk(
            db,
            {
                "waste_category": result.get("category"),
                "contamination_level": item.contamination_level or "low",
                "quantity": item.quantity,
                "waiting_duration_hours": 0,
                "damaged_seal": str(item.condition or "").lower() in {"damaged", "broken"},
                "leakage": str(item.contamination_level or "").lower() in {"high", "severe"},
                "incident_flag": False,
                "urgency": "routine",
            },
        )
        item.risk_score = risk_result.get("score")
        item.risk_priority = risk_result.get("priority")
        classified_items.append({
            "id": item.id,
            "item_name": item.item_name,
            "category": item.category,
            "segregation_group": item.segregation_group,
            "confidence": item.classification_confidence,
            "risk_priority": item.risk_priority,
            "guidance": item.classification_guidance,
        })

    passport.risk_priority = _priority_for_score(max((float(item.risk_score) for item in passport.items if item.risk_score is not None), default=0.0))
    passport.status = "CLASSIFIED"
    _add_event(db, passport, "CLASSIFIED", "Waste items classified using segregation rules.", current_user.name)
    db.commit()
    db.refresh(passport)
    return {"id": passport.id, "passport_number": passport.passport_number, "status": passport.status, "risk_priority": passport.risk_priority, "classified_items": classified_items}


@router.post("/{passport_id}/risk")
async def assess_passport_risk(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)

    if not passport.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passport does not contain any items to assess.")

    scores = []
    for item in passport.items:
        risk_result = assess_risk(
            db,
            {
                "waste_category": item.category or "General Biomedical Waste",
                "contamination_level": item.contamination_level or "low",
                "quantity": item.quantity,
                "waiting_duration_hours": 0,
                "damaged_seal": str(item.condition or "").lower() in {"damaged", "broken"},
                "leakage": str(item.contamination_level or "").lower() in {"high", "severe"},
                "incident_flag": False,
                "urgency": "routine",
            },
        )
        scores.append(float(risk_result.get("score") or 0))
        item.risk_score = float(risk_result.get("score") or 0)
        item.risk_priority = risk_result.get("priority")

    highest = max(scores)
    passport.risk_priority = _priority_for_score(highest)
    db.commit()
    return {"risk_priority": passport.risk_priority, "score": round(highest, 2), "items": [
        {"id": item.id, "item_name": item.item_name, "risk_score": item.risk_score, "risk_priority": item.risk_priority}
        for item in passport.items
    ]}


@router.post("/{passport_id}/status")
async def update_passport_status(
    passport_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)

    new_status = str(payload.get("status") or "").upper()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status requested.")
    if new_status not in ALLOWED_STATUS_TRANSITIONS.get(passport.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Status transition from {passport.status} to {new_status} is not allowed.")

    passport.status = new_status
    passport.updated_at = _utc_now()
    _add_event(db, passport, "STATUS_UPDATED", f"Status changed to {new_status}", current_user.name)
    db.commit()
    db.refresh(passport)
    return _serialize_passport(passport, db)


@router.get("/{passport_id}/events")
async def get_passport_events(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)
    events = db.query(WastePassportEvent).filter(WastePassportEvent.passport_id == passport_id).order_by(WastePassportEvent.created_at.asc()).all()
    return [{"id": event.id, "event_type": event.event_type, "details": event.details, "actor_name": event.actor_name, "created_at": event.created_at} for event in events]


@router.post("/{passport_id}/generate-qr")
async def generate_qr(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    _ensure_facility_access(current_user, passport.facility_id)

    passport.qr_token = secrets.token_urlsafe(24)
    passport.qr_generated_at = _utc_now()
    db.commit()
    payload = _serialize_passport(passport, db)
    payload["qr_data_url"] = _generate_qr_data_url()
    payload["qr_token"] = passport.qr_token
    _add_event(db, passport, "QR_GENERATED", "QR code generated for passport traceability.", current_user.name)
    return payload


@qr_router.post("/validate")
async def validate_qr_token(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token") if isinstance(payload, dict) else None
    if not token or not str(token).strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid QR token is required.")
    passport = db.query(WastePassport).filter(WastePassport.qr_token == token).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR token is invalid or expired.")
    facility = db.query(Facility).filter(Facility.id == passport.facility_id).first()
    ward = db.query(Ward).filter(Ward.id == passport.ward_id).first() if passport.ward_id else None
    latest_category = next((item.category for item in passport.items if item.category), None)
    return {
        "passport_number": passport.passport_number,
        "status": passport.status,
        "facility_id": passport.facility_id,
        "facility_name": facility.name if facility else None,
        "ward_id": passport.ward_id,
        "ward_name": ward.name if ward else None,
        "risk_priority": passport.risk_priority,
        "waste_category": latest_category,
        "total_weight_kg": passport.total_weight_kg,
        "message": "QR token validated successfully.",
    }
