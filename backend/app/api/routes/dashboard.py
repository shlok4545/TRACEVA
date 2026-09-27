from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.analytics_service import dashboard_summary, recent_activity

router = APIRouter()


@router.get("/summary")
async def dashboard_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_summary(db, current_user)


@router.get("/activity")
async def dashboard_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return recent_activity(db, current_user)


@router.get("")
async def dashboard_root() -> dict[str, Any]:
    return {"message": "Dashboard API online"}
