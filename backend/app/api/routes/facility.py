from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.facility import Facility
from app.models.transport import TreatmentEvidence, TreatmentRecord, TransportEvent
from app.models.user import User
from app.models.waste import WastePassport, WastePassportEvent

router = APIRouter()
ALLOWED_EVIDENCE_TYPES = {"application/pdf", "image/jpeg", "image/png"}
VALID_RECEIVE_STATUSES = {"INTACT", "DAMAGED", "LEAKING", "UNKNOWN"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_receipt(passport: WastePassport, db: Session) -> dict[str, Any]:
    latest_transport = (
        db.query(TransportEvent)
        .filter(TransportEvent.passport_id == passport.id)
        .order_by(TransportEvent.created_at.desc())
        .first()
    )
    latest_record = (
        db.query(TreatmentRecord)
        .filter(TreatmentRecord.passport_id == passport.id)
        .order_by(TreatmentRecord.created_at.desc())
        .first()
    )
    return {
        "passport_id": passport.id,
        "passport_number": passport.passport_number,
        "status": passport.status,
        "risk_priority": passport.risk_priority,
        "facility_id": passport.facility_id,
        "transport_status": latest_transport.event_type if latest_transport else None,
        "treatment_status": latest_record.verification_status if latest_record else None,
        "received_at": latest_record.received_at if latest_record else None,
        "seal_condition": latest_record.seal_condition if latest_record else None,
    }


@router.get("/receiving")
async def list_receiving_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN", "REGULATOR"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facilities can access receiving queues.")
    passports = db.query(WastePassport).filter(WastePassport.status.in_({"IN_TRANSIT", "AT_TREATMENT"})).all()
    return [_serialize_receipt(passport, db) for passport in passports]


@router.get("/receiving/{passport_id}")
async def get_receiving_detail(
    passport_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN", "REGULATOR"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facilities can access receiving details.")
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != 4:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not allowed to receive waste at this treatment facility.")
    return _serialize_receipt(passport, db)


@router.post("/receiving/{passport_id}/accept")
async def accept_received_waste(
    passport_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN", "REGULATOR"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the treatment facility can accept receiving records.")
    if current_user.role not in {"ADMIN", "REGULATOR"} and current_user.facility_id != 4:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This facility is not the treatment facility.")
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receiving payload is required.")

    seal_condition = str(payload.get("seal_condition") or "INTACT").upper()
    if seal_condition not in VALID_RECEIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="seal_condition must be one of INTACT, DAMAGED, LEAKING, UNKNOWN.")

    record = db.query(TreatmentRecord).filter(TreatmentRecord.passport_id == passport.id).order_by(TreatmentRecord.created_at.desc()).first()
    receipt_status = "PENDING"
    if seal_condition in {"DAMAGED", "LEAKING"}:
        receipt_status = "REQUIRES_REVIEW"

    if record is not None:
        record.received_by_user_id = current_user.id
        record.received_at = record.received_at or _utc_now()
        record.received_weight_kg = float(payload.get("received_weight_kg") or record.received_weight_kg or 0.0)
        record.seal_condition = seal_condition
        record.intake_status = "RECEIVED"
        record.verification_status = record.verification_status or receipt_status
        record.updated_at = _utc_now()
        receipt_status = record.verification_status

    passport.status = "AT_TREATMENT"
    passport.updated_at = _utc_now()
    db.add(WastePassportEvent(passport_id=passport.id, event_type="RECEIVED_AT_TREATMENT", details=f"Waste received with seal condition {seal_condition}", actor_name=current_user.name))
    db.commit()
    return {
        "passport_id": passport.id,
        "treatment_facility_id": 4,
        "received_by_user_id": current_user.id,
        "received_at": _utc_now(),
        "received_weight_kg": float(payload.get("received_weight_kg") or 0.0),
        "seal_condition": seal_condition,
        "intake_status": "RECEIVED",
        "verification_status": receipt_status,
    }


@router.post("/receiving/{passport_id}/reject")
async def reject_received_waste(
    passport_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN", "REGULATOR"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facilities can reject receiving records.")
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")
    reason = str((payload or {}).get("reason") or "Rejected at treatment receiving stage").strip()
    passport.status = "REJECTED"
    passport.updated_at = _utc_now()
    db.add(WastePassportEvent(passport_id=passport.id, event_type="REJECTED_AT_TREATMENT", details=reason, actor_name=current_user.name))
    db.commit()
    return {"passport_id": passport.id, "status": passport.status, "reason": reason}


@router.post("/{record_id}/evidence")
async def upload_treatment_evidence(
    record_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment staff can upload treatment evidence.")
    record = db.query(TreatmentRecord).filter(TreatmentRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment record not found.")
    if file.content_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF or JPG/PNG evidence is supported.")
    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    existing_name = file.filename or "evidence"
    evidence = TreatmentEvidence(
        treatment_record_id=record.id,
        file_name=existing_name,
        file_type=file.content_type,
        file_path=f"/tmp/{existing_name}",
        uploaded_by_user_id=current_user.id,
        description="Treatment verification evidence",
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return {"id": evidence.id, "file_name": evidence.file_name, "file_type": evidence.file_type, "uploaded_at": evidence.uploaded_at}
