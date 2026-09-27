from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.database import get_db
from app.models.facility import Facility
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()


def serialize_user(user: User, db: Session) -> UserResponse:
    facility = db.query(Facility).filter(Facility.id == user.facility_id).first() if user.facility_id else None
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
        ward_name=None,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown email or password.")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown email or password.")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        facility_id=user.facility_id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, user=serialize_user(user, db))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    return serialize_user(current_user, db)


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        return {"message": "No active session to logout."}
    return {"message": "Logout successful."}
