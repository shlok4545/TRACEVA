from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.analytics_service import (
    csv_export,
    dashboard_summary,
    facility_report,
    pickup_report,
    risk_report,
    summarize_treatment,
    traceability_report,
)

router = APIRouter()


@router.get("/summary")
async def dashboard_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_summary(db, current_user)


@router.get("/risk")
async def risk_analytics(
    range: str | None = Query(default=None, alias="range"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return risk_report(db, current_user, range, start_date, end_date)


@router.get("/pickups")
async def pickup_analytics(
    range: str | None = Query(default=None, alias="range"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return pickup_report(db, current_user, range, start_date, end_date)


@router.get("/treatment")
async def treatment_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return summarize_treatment(db, current_user)


@router.get("/traceability")
async def traceability_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return traceability_report(db, current_user)


@router.get("/facilities")
async def facilities_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return facility_report(db, current_user)


@router.get("/incidents/export")
async def export_incidents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.incident import Incident
    rows = [
        {"incident_number": item.incident_number, "severity": item.severity, "status": item.status, "facility_id": item.facility_id, "title": item.title}
        for item in db.query(Incident).all()
    ]
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        rows = [row for row in rows if row["facility_id"] == (current_user.facility_id or -1)]
    csv = csv_export(rows, ["incident_number", "severity", "status", "facility_id", "title"])
    return {"csv": csv}


@router.get("/pickups/export")
async def export_pickups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.pickup import PickupRequest
    rows = [{"id": item.id, "status": item.status, "priority": item.priority, "facility_id": item.facility_id, "passport_id": item.passport_id} for item in db.query(PickupRequest).all()]
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        rows = [row for row in rows if row["facility_id"] == (current_user.facility_id or -1)]
    csv = csv_export(rows, ["id", "status", "priority", "facility_id", "passport_id"])
    return {"csv": csv}


@router.get("/traceability/export")
async def export_traceability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.waste import WastePassport
    rows = [{"passport_number": item.passport_number, "status": item.status, "facility_id": item.facility_id, "risk_priority": item.risk_priority} for item in db.query(WastePassport).all()]
    if current_user.role not in {"ADMIN", "REGULATOR"}:
        rows = [row for row in rows if row["facility_id"] == (current_user.facility_id or -1)]
    csv = csv_export(rows, ["passport_number", "status", "facility_id", "risk_priority"])
    return {"csv": csv}


@router.get("/dashboard")
async def dashboard_root() -> dict[str, Any]:
    return {"message": "Dashboard and analytics service is available."}


@router.get("")
async def reports() -> dict[str, Any]:
    return {"message": "Reports service online."}
