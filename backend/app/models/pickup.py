from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CollectorProfile(Base):
    __tablename__ = "collector_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    employee_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    availability_status: Mapped[str] = mapped_column(String(30), nullable=False, default="AVAILABLE", index=True)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_update: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    user = relationship("User", back_populates="collector_profile")
    facility = relationship("Facility", back_populates="collector_profiles")
    assigned_pickups = relationship("PickupRequest", back_populates="assigned_collector")


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_collector_id: Mapped[int | None] = mapped_column(ForeignKey("collector_profiles.id"), nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", index=True)
    risk_score_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED", index=True)
    requested_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    assigned_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    accepted_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pickup_started_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    due_at: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    facility = relationship("Facility", back_populates="pickup_requests")
    passport = relationship("WastePassport", back_populates="pickup_requests")
    assigned_collector = relationship("CollectorProfile", back_populates="assigned_pickups")
    events = relationship("PickupEvent", back_populates="pickup_request", cascade="all, delete-orphan")
    transport_events = relationship("TransportEvent", back_populates="pickup_request", cascade="all, delete-orphan")


class PickupEvent(Base):
    __tablename__ = "pickup_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pickup_request_id: Mapped[int] = mapped_column(ForeignKey("pickup_requests.id"), nullable=False, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    collector_id: Mapped[int | None] = mapped_column(ForeignKey("collector_profiles.id"), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    pickup_request = relationship("PickupRequest", back_populates="events")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="INFO", index=True)
    related_passport_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    related_pickup_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    related_incident_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    read_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
