from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.database import get_db
from app.models.facility import Facility
from app.models.user import User
from app.models.ward import Ward
from app.schemas.auth import FacilityCreate, FacilityResponse, FacilityUpdate

router = APIRouter()


def serialize_facility(facility: Facility, db: Session) -> FacilityResponse:
    ward_count = db.query(Ward).filter(Ward.facility_id == facility.id).count()
    return FacilityResponse(
        id=facility.id,
        name=facility.name,
        type=facility.type,
        address=facility.address,
        contact=facility.contact,
        latitude=facility.latitude,
        longitude=facility.longitude,
        status=facility.status,
        created_at=facility.created_at,
        ward_count=ward_count,
    )


@router.get("", response_model=list[FacilityResponse])
async def list_facilities(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[FacilityResponse]:
    if current_user.role == "REGULATOR":
        facilities = db.query(Facility).all()
    elif current_user.role in {"ADMIN", "WARD_STAFF", "COLLECTOR", "TREATMENT_FACILITY"}:
        facilities = db.query(Facility).filter(Facility.id == current_user.facility_id).all() if current_user.facility_id else []
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to facilities.")
    return [serialize_facility(facility, db) for facility in facilities]


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(facility_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FacilityResponse:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    if current_user.role != "ADMIN" and current_user.role != "REGULATOR" and current_user.facility_id != facility.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This facility is not available to your account.")
    return serialize_facility(facility, db)


@router.post("", response_model=FacilityResponse)
async def create_facility(payload: FacilityCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("ADMIN"))) -> FacilityResponse:
    facility = Facility(
        name=payload.name,
        type=payload.type,
        address=payload.address,
        contact=payload.contact,
        latitude=payload.latitude,
        longitude=payload.longitude,
        status=payload.status.upper(),
    )
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return serialize_facility(facility, db)


@router.put("/{facility_id}", response_model=FacilityResponse)
async def update_facility(facility_id: int, payload: FacilityUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role("ADMIN"))) -> FacilityResponse:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if facility is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Facility not found.")
    if payload.name is not None:
        facility.name = payload.name
    if payload.type is not None:
        facility.type = payload.type
    if payload.address is not None:
        facility.address = payload.address
    if payload.contact is not None:
        facility.contact = payload.contact
    if payload.latitude is not None:
        facility.latitude = payload.latitude
    if payload.longitude is not None:
        facility.longitude = payload.longitude
    if payload.status is not None:
        facility.status = payload.status.upper()
    db.commit()
    db.refresh(facility)
    return serialize_facility(facility, db)
