from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.models.incident import Incident
from app.models.pickup import PickupRequest
from app.models.transport import TreatmentRecord
from app.models.user import User
from app.models.waste import WastePassport


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _apply_scope(user: User, query):
    if user.role in {"ADMIN", "REGULATOR"}:
        return query
    if user.facility_id is None:
        return query.filter(False)
    return query.filter_by(facility_id=user.facility_id)


def _range_to_dates(range_name: str | None, start_date: str | None, end_date: str | None):
    end = _parse_iso(end_date) if end_date else _utc_now()
    if range_name == "today":
        start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_name == "last_7_days":
        start = end - timedelta(days=7)
    elif range_name == "last_30_days":
        start = end - timedelta(days=30)
    elif start_date:
        start = _parse_iso(start_date) or (end - timedelta(days=30))
    else:
        start = end - timedelta(days=30)
    return start, end


def summarize_passports(db: Session, user: User) -> dict[str, Any]:
    query = db.query(WastePassport)
    query = _apply_scope(user, query)
    passports = query.all()
    total = len(passports)
    active = sum(1 for p in passports if p.status not in {"COMPLETED", "CLOSED", "REJECTED"})
    completed = sum(1 for p in passports if p.status == "COMPLETED")
    total_weight = round(sum(float(p.total_weight_kg or 0) for p in passports), 2)
    return {"total": total, "active": active, "completed": completed, "total_weight_kg": total_weight}


def summarize_risk(db: Session, user: User) -> dict[str, Any]:
    query = db.query(WastePassport)
    query = _apply_scope(user, query)
    passports = query.all()
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for passport in passports:
        level = (passport.risk_priority or "LOW").lower()
        if level in counts:
            counts[level] += 1
    total = sum(counts.values()) or 1
    distribution = {k: round((v / total) * 100, 2) for k, v in counts.items()}
    return {**counts, "distribution": distribution}


def summarize_pickups(db: Session, user: User, range_name: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    query = db.query(PickupRequest)
    query = _apply_scope(user, query)
    start, end = _range_to_dates(range_name, start_date, end_date)
    if start and end:
        query = query.filter(PickupRequest.requested_at.isnot(None))
        filtered = []
        for request in query.all():
            requested = _parse_iso(request.requested_at)
            if requested and start <= requested <= end:
                filtered.append(request)
    else:
        filtered = query.all()
    total_requests = len(filtered)
    completed = sum(1 for r in filtered if r.status == "COLLECTED")
    pending = sum(1 for r in filtered if r.status not in {"COLLECTED", "CANCELLED"})
    overdue = sum(1 for r in filtered if r.status not in {"COLLECTED", "CANCELLED"} and r.due_at and _parse_iso(r.due_at) and _parse_iso(r.due_at) < _utc_now())
    response_times = []
    waiting_times = []
    for r in filtered:
        requested = _parse_iso(r.requested_at)
        started = _parse_iso(r.pickup_started_at)
        if requested and started:
            response_times.append((started - requested).total_seconds() / 60)
        if requested:
            waiting_times.append(((_utc_now() - requested).total_seconds() / 60 if r.status not in {"COLLECTED", "CANCELLED"} else max(0.0, min(10000.0, (( _parse_iso(r.completed_at) or _utc_now() ) - requested).total_seconds() / 60))))
    avg_wait = round(sum(waiting_times) / len(waiting_times), 2) if waiting_times else 0
    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else 0
    return {
        "total_requests": total_requests,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "average_waiting_time_minutes": avg_wait,
        "average_response_time_minutes": avg_response,
        "priority_distribution": {"CRITICAL": sum(1 for r in filtered if r.priority == "CRITICAL"), "HIGH": sum(1 for r in filtered if r.priority == "HIGH"), "MEDIUM": sum(1 for r in filtered if r.priority == "MEDIUM"), "LOW": sum(1 for r in filtered if r.priority == "LOW")},
    }


def summarize_treatment(db: Session, user: User) -> dict[str, Any]:
    records = db.query(TreatmentRecord).all()
    if user.role not in {"ADMIN", "REGULATOR"}:
        records = [r for r in records if r.passport and r.passport.facility_id == user.facility_id]
    received = len(records)
    treatment_pending = sum(1 for r in records if r.intake_status == "PENDING")
    treatment_completed = sum(1 for r in records if r.treatment_completed_at is not None)
    verification_pending = sum(1 for r in records if r.verification_status == "PENDING")
    verified = sum(1 for r in records if r.verification_status == "VERIFIED")
    rejected = sum(1 for r in records if r.intake_status == "REJECTED")
    timings = []
    for r in records:
        if r.received_at and r.treatment_completed_at:
            try:
                start = _parse_iso(r.received_at)
                end = _parse_iso(r.treatment_completed_at)
                if start and end:
                    timings.append((end - start).total_seconds() / 3600)
            except Exception:
                pass
    avg_hours = round(sum(timings) / len(timings), 2) if timings else 0
    return {
        "received_count": received,
        "treatment_pending": treatment_pending,
        "treatment_completed": treatment_completed,
        "verification_pending": verification_pending,
        "verified": verified,
        "rejected": rejected,
        "average_treatment_completion_hours": avg_hours,
    }


def traceability_summary(db: Session, user: User) -> dict[str, Any]:
    passports = db.query(WastePassport)
    passports = _apply_scope(user, passports).all()
    stages = [
        "Created",
        "Classified",
        "QR Generated",
        "Pickup Requested",
        "Collected",
        "Transported",
        "Received",
        "Treatment Completed",
        "Verified",
        "Closed",
    ]
    counts = {stage: 0 for stage in stages}
    for passport in passports:
        if passport.created_at:
            counts["Created"] += 1
        if passport.qr_generated_at:
            counts["QR Generated"] += 1
        if passport.status in {"READY_FOR_PICKUP", "IN_TRANSIT", "AT_TREATMENT", "COMPLETED", "CLOSED"}:
            counts["Pickup Requested"] += 1
        if passport.status in {"IN_TRANSIT", "AT_TREATMENT", "COMPLETED", "CLOSED"}:
            counts["Transported"] += 1
        if passport.status in {"AT_TREATMENT", "COMPLETED", "CLOSED"}:
            counts["Received"] += 1
        if passport.status in {"COMPLETED", "CLOSED"}:
            counts["Treatment Completed"] += 1
            counts["Verified"] += 1
        if passport.status == "CLOSED":
            counts["Closed"] += 1
    total = max(1, len(passports))
    completion_rate = round((counts["Closed"] / total) * 100, 2)
    return {"stages": counts, "completion_rate": completion_rate, "total_passports": total}


def facility_summary(db: Session, user: User) -> list[dict[str, Any]]:
    query = db.query(Facility)
    if user.role not in {"ADMIN", "REGULATOR"}:
        query = query.filter(Facility.id == (user.facility_id or -1))
    facilities = query.all()
    rows = []
    for facility in facilities:
        passports = db.query(WastePassport).filter(WastePassport.facility_id == facility.id).all()
        incidents = db.query(Incident).filter(Incident.facility_id == facility.id).count()
        rows.append({
            "facility_id": facility.id,
            "facility_name": facility.name,
            "passport_volume": len(passports),
            "waste_weight_kg": round(sum(float(p.total_weight_kg or 0) for p in passports), 2),
            "incident_count": incidents,
            "traceability_completion_rate": round((sum(1 for p in passports if p.status == "CLOSED") / max(1, len(passports))) * 100, 2),
        })
    return rows


def recent_activity(db: Session, user: User) -> list[dict[str, Any]]:
    rows = []
    for model, event_name, entity_name in [
        (WastePassport, "status", "passport"),
        (Incident, "incident", "incident"),
        (PickupRequest, "pickup", "pickup"),
        (TreatmentRecord, "treatment", "treatment_record"),
    ]:
        for item in db.query(model).all():
            if model is WastePassport:
                rows.append({"event_type": item.status, "timestamp": item.updated_at, "entity": entity_name, "actor": "system", "message": f"Passport {item.passport_number} updated to {item.status}.", "severity": "medium"})
            elif model is Incident:
                rows.append({"event_type": "incident", "timestamp": item.created_at, "entity": entity_name, "actor": item.incident_number, "message": item.title, "severity": item.severity.lower()})
            elif model is PickupRequest:
                rows.append({"event_type": "pickup", "timestamp": item.updated_at, "entity": entity_name, "actor": str(item.id), "message": f"Pickup request {item.id} is {item.status}.", "severity": "low"})
            else:
                rows.append({"event_type": "treatment", "timestamp": item.updated_at, "entity": entity_name, "actor": str(item.id), "message": f"Treatment record {item.id} status {item.verification_status}.", "severity": "medium"})
    rows.sort(key=lambda row: row["timestamp"] or "", reverse=True)
    return rows[:10]


def dashboard_summary(db: Session, user: User) -> dict[str, Any]:
    from app.services.incident_service import build_alerts

    passport_summary = summarize_passports(db, user)
    risk_summary = summarize_risk(db, user)
    pickup_summary = summarize_pickups(db, user)
    treatment_summary = summarize_treatment(db, user)
    incident_summary = {
        "total": db.query(Incident).count() if user.role in {"ADMIN", "REGULATOR"} else db.query(Incident).filter(Incident.facility_id == (user.facility_id or -1)).count(),
        "open": db.query(Incident).filter(Incident.status == "OPEN").count() if user.role in {"ADMIN", "REGULATOR"} else db.query(Incident).filter(Incident.facility_id == (user.facility_id or -1), Incident.status == "OPEN").count(),
        "resolved": db.query(Incident).filter(Incident.status == "RESOLVED").count() if user.role in {"ADMIN", "REGULATOR"} else db.query(Incident).filter(Incident.facility_id == (user.facility_id or -1), Incident.status == "RESOLVED").count(),
    }
    return {
        "passport_summary": passport_summary,
        "risk_summary": risk_summary,
        "pickup_summary": pickup_summary,
        "treatment_summary": treatment_summary,
        "incident_summary": incident_summary,
        "alerts": build_alerts(db, user),
        "recent_activity": recent_activity(db, user),
    }


def risk_report(db: Session, user: User, range_name: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    summary = summarize_risk(db, user)
    start, end = _range_to_dates(range_name, start_date, end_date)
    return {"low": summary["low"], "medium": summary["medium"], "high": summary["high"], "critical": summary["critical"], "distribution": summary["distribution"], "trend": [{"date": _iso(start + timedelta(days=i)), "value": 0} for i in range((end - start).days + 1)]}


def pickup_report(db: Session, user: User, range_name: str | None = None, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    return summarize_pickups(db, user, range_name, start_date, end_date)


def treatment_report(db: Session, user: User) -> dict[str, Any]:
    return summarize_treatment(db, user)


def traceability_report(db: Session, user: User) -> dict[str, Any]:
    return traceability_summary(db, user)


def facility_report(db: Session, user: User) -> list[dict[str, Any]]:
    return facility_summary(db, user)


def csv_export(rows: list[dict[str, Any]], columns: list[str]) -> str:
    import csv
    import io

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in columns})
    return output.getvalue()
