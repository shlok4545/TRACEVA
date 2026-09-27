from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        token_data = decode_access_token(credentials.credentials)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

    return user


def require_role(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource.")
        return current_user

    return dependency


def require_any_role(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this resource.")
        return current_user

    return dependency


def require_facility_access(facility_id: int | None):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == "ADMIN":
            return current_user
        if facility_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility access is required.")
        if current_user.facility_id != facility_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This facility is not available to your account.")
        return current_user

    return dependency


def require_resource_access(resource_facility_id: int | None):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == "ADMIN":
            return current_user
        if current_user.role == "REGULATOR":
            return current_user
        if resource_facility_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facility context is missing.")
        if current_user.facility_id != resource_facility_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only access records for your own facility.")
        return current_user

    return dependency
