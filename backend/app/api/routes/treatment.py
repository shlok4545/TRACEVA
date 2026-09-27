from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.transport import TreatmentEvidence, TreatmentRecord, TransportEvent
from app.models.user import User
from app.models.waste import WastePassport, WastePassportEvent

router = APIRouter()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_record(record: TreatmentRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "passport_id": record.passport_id,
        "treatment_facility_id": record.treatment_facility_id,
        "received_by_user_id": record.received_by_user_id,
        "received_at": record.received_at,
        "received_weight_kg": record.received_weight_kg,
        "seal_condition": record.seal_condition,
        "intake_status": record.intake_status,
        "treatment_method": record.treatment_method,
        "treatment_started_at": record.treatment_started_at,
        "treatment_completed_at": record.treatment_completed_at,
        "verification_status": record.verification_status,
        "certificate_number": record.certificate_number,
        "verification_notes": record.verification_notes,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "evidence": [
            {
                "id": evidence.id,
                "file_name": evidence.file_name,
                "file_type": evidence.file_type,
                "uploaded_at": evidence.uploaded_at,
                "description": evidence.description,
            }
            for evidence in record.evidence
        ],
    }


@router.get("/records")
async def list_treatment_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN", "REGULATOR"}:
        return []
    query = db.query(TreatmentRecord)
    if current_user.role == "TREATMENT_FACILITY":
        query = query.filter(TreatmentRecord.treatment_facility_id == current_user.facility_id)
    return [_serialize_record(record) for record in query.order_by(TreatmentRecord.created_at.desc()).all()]


@router.post("/records")
async def create_treatment_record(
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facility staff can create treatment records.")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Treatment payload is required.")

    passport_id = int(payload.get("passport_id"))
    passport = db.query(WastePassport).filter(WastePassport.id == passport_id).first()
    if passport is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passport not found.")

    latest_transport = (
        db.query(TransportEvent)
        .filter(TransportEvent.passport_id == passport_id)
        .order_by(TransportEvent.created_at.desc())
        .first()
    )
    if latest_transport is None or latest_transport.event_type not in {"TRANSPORT_ARRIVED"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Treatment can only begin after waste has been received at the treatment facility.")

    if current_user.role != "ADMIN" and current_user.facility_id != 4:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not allowed to create treatment records.")

    if db.query(TreatmentRecord).filter(TreatmentRecord.passport_id == passport_id).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A treatment record already exists for this passport.")

    record = TreatmentRecord(
        passport_id=passport.id,
        treatment_facility_id=current_user.facility_id or 4,
        received_by_user_id=current_user.id,
        received_at=_utc_now(),
        received_weight_kg=float(payload.get("received_weight_kg") or 0.0),
        seal_condition=str(payload.get("seal_condition") or "INTACT").upper(),
        intake_status="RECEIVED",
        treatment_method=str(payload.get("treatment_method") or "").strip() or "Unspecified treatment",
        verification_status="PENDING",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    passport.status = "AT_TREATMENT"
    passport.updated_at = _utc_now()
    db.add(WastePassportEvent(passport_id=passport.id, event_type="TREATMENT_RECORD_CREATED", details=f"Treatment record created using {record.treatment_method}", actor_name=current_user.name))
    db.commit()
    return _serialize_record(record)


@router.get("/records/{record_id}")
async def get_treatment_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(TreatmentRecord).filter(TreatmentRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment record not found.")
    if current_user.role == "TREATMENT_FACILITY" and current_user.facility_id != record.treatment_facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This treatment record belongs to another facility.")
    return _serialize_record(record)


@router.put("/records/{record_id}")
async def update_treatment_record(
    record_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facility staff can update treatment records.")
    record = db.query(TreatmentRecord).filter(TreatmentRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment record not found.")
    if current_user.role != "ADMIN" and current_user.facility_id != record.treatment_facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This treatment record belongs to another facility.")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Update payload is required.")

    if "treatment_method" in payload and payload.get("treatment_method") is not None:
        record.treatment_method = str(payload["treatment_method"]).strip() or record.treatment_method
    if "received_weight_kg" in payload and payload.get("received_weight_kg") is not None:
        record.received_weight_kg = float(payload["received_weight_kg"])
    if "seal_condition" in payload and payload.get("seal_condition") is not None:
        record.seal_condition = str(payload["seal_condition"]).upper()
    if "treatment_started_at" in payload and payload.get("treatment_started_at") is not None:
        record.treatment_started_at = str(payload["treatment_started_at"])
    if "treatment_completed_at" in payload and payload.get("treatment_completed_at") is not None:
        record.treatment_completed_at = str(payload["treatment_completed_at"])
    if "verification_status" in payload and payload.get("verification_status") is not None:
        record.verification_status = str(payload["verification_status"]).upper()
    record.updated_at = _utc_now()
    db.commit()
    return _serialize_record(record)


@router.put("/records/{record_id}/verify")
async def verify_treatment_record(
    record_id: int,
    payload: dict[str, Any] | None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"TREATMENT_FACILITY", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only treatment facility staff can verify treatment records.")
    record = db.query(TreatmentRecord).filter(TreatmentRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Treatment record not found.")
    if current_user.role != "ADMIN" and current_user.facility_id != record.treatment_facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This treatment record belongs to another facility.")
    if record.verification_status == "VERIFIED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This treatment record has already been verified.")
    if not record.treatment_started_at or not record.treatment_completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Treatment start and completion timestamps are required before verification.")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification payload is required.")

    record.verification_status = "VERIFIED"
    record.certificate_number = str(payload.get("certificate_number") or "").strip() or record.certificate_number
    record.verification_notes = str(payload.get("verification_notes") or "").strip() or record.verification_notes
    record.updated_at = _utc_now()
    passport = db.query(WastePassport).filter(WastePassport.id == record.passport_id).first()
    if passport is not None:
        passport.status = "COMPLETED"
        passport.updated_at = _utc_now()
        db.add(WastePassportEvent(passport_id=passport.id, event_type="TREATMENT_VERIFIED", details=f"Treatment verified with certificate {record.certificate_number}", actor_name=current_user.name))
    db.commit()
    return _serialize_record(record)


@router.post("/records/{record_id}/evidence")
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
    if current_user.role != "ADMIN" and current_user.facility_id != record.treatment_facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This treatment record belongs to another facility.")
    if file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF or JPG/PNG evidence is supported.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    evidence = TreatmentEvidence(
        treatment_record_id=record.id,
        file_name=file.filename or "evidence",
        file_type=file.content_type,
        file_path=f"/tmp/{file.filename or 'evidence'}",
        uploaded_by_user_id=current_user.id,
        description="Treatment verification evidence",
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return {"id": evidence.id, "file_name": evidence.file_name, "file_type": evidence.file_type, "uploaded_at": evidence.uploaded_at}
