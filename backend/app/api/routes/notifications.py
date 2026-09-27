from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.pickup import Notification
from app.models.user import User

router = APIRouter()


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("")
async def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Notification)
        .filter(Notification.user_id.in_([current_user.id, None]))
        .order_by(Notification.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "notification_type": item.notification_type,
                "severity": item.severity,
                "title": item.title,
                "message": item.message,
                "related_passport_id": item.related_passport_id,
                "related_pickup_id": item.related_pickup_id,
                "related_incident_id": item.related_incident_id,
                "is_read": item.is_read,
                "created_at": item.created_at,
                "read_at": item.read_at,
            }
            for item in items
        ],
        "unread_count": sum(1 for item in items if not item.is_read),
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    if notification.user_id not in (current_user.id, None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Notification unavailable in your scope.")
    notification.is_read = True
    notification.read_at = _iso_now()
    db.commit()
    return {"id": notification.id, "status": "read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = db.query(Notification).filter(Notification.user_id.in_([current_user.id, None]), Notification.is_read.is_(False)).all()
    for item in items:
        item.is_read = True
        item.read_at = _iso_now()
    db.commit()
    return {"updated": len(items)}
