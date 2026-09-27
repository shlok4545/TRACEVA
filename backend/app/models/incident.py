from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    incident_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    passport_id: Mapped[int | None] = mapped_column(ForeignKey("waste_passports.id"), nullable=True, index=True)
    pickup_request_id: Mapped[int | None] = mapped_column(ForeignKey("pickup_requests.id"), nullable=True, index=True)
    reported_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    incident_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    detected_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    acknowledged_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    facility = relationship("Facility", back_populates="incidents")
    reported_by = relationship("User", foreign_keys="[Incident.reported_by_user_id]", back_populates="reported_incidents")
    assigned_to = relationship("User", foreign_keys="[Incident.assigned_to_user_id]", back_populates="assigned_incidents")
