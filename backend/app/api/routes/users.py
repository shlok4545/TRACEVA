from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.core.security import get_password_hash
from app.db.database import get_db
from app.models.facility import Facility
from app.models.user import User
from app.models.ward import Ward
from app.schemas.auth import UserCreate, UserResponse, UserUpdate

router = APIRouter()


def serialize_user(user: User, db: Session) -> UserResponse:
    facility = db.query(Facility).filter(Facility.id == user.facility_id).first() if user.facility_id else None
    ward = db.query(Ward).filter(Ward.id == user.ward_id).first() if user.ward_id else None
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        facility_id=user.facility_id,
        ward_id=user.ward_id,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
        facility_name=facility.name if facility else None,
        ward_name=ward.name if ward else None,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("ADMIN", "REGULATOR", "WARD_STAFF", "TREATMENT_FACILITY", "COLLECTOR")),
) -> list[UserResponse]:
    users = db.query(User).all()
    return [serialize_user(user, db) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if current_user.role != "ADMIN" and current_user.id != user.id and current_user.facility_id != user.facility_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This user is outside your facility access.")
    return serialize_user(user, db)


@router.post("", response_model=UserResponse)
async def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role("ADMIN"))) -> UserResponse:
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists.")
    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role=payload.role.upper(),
        facility_id=payload.facility_id,
        ward_id=payload.ward_id,
        status=payload.status.upper(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user, db)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role("ADMIN"))) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email.lower()
    if payload.password is not None:
        user.password_hash = get_password_hash(payload.password)
    if payload.role is not None:
        user.role = payload.role.upper()
    if payload.facility_id is not None:
        user.facility_id = payload.facility_id
    if payload.ward_id is not None:
        user.ward_id = payload.ward_id
    if payload.status is not None:
        user.status = payload.status.upper()
    db.commit()
    db.refresh(user)
    return serialize_user(user, db)
