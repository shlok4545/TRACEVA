from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class TransportEvent(Base):
    __tablename__ = "transport_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pickup_request_id: Mapped[int] = mapped_column(ForeignKey("pickup_requests.id"), nullable=False, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    collector_id: Mapped[int | None] = mapped_column(ForeignKey("collector_profiles.id"), nullable=True, index=True)
    related_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    from_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    to_facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    departure_time: Mapped[str | None] = mapped_column(String(30), nullable=True)
    arrival_time: Mapped[str | None] = mapped_column(String(30), nullable=True)
    seal_status: Mapped[str] = mapped_column(String(30), nullable=False, default="INTACT")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    pickup_request = relationship("PickupRequest", back_populates="transport_events")
    passport = relationship("WastePassport", back_populates="transport_events")


class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    treatment_facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    received_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    received_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    received_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    seal_condition: Mapped[str | None] = mapped_column(String(30), nullable=True)
    intake_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    treatment_method: Mapped[str | None] = mapped_column(String(200), nullable=True)
    treatment_started_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    treatment_completed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    certificate_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    passport = relationship("WastePassport", back_populates="treatment_records")
    evidence = relationship("TreatmentEvidence", back_populates="record", cascade="all, delete-orphan")


class TreatmentEvidence(Base):
    __tablename__ = "treatment_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    treatment_record_id: Mapped[int] = mapped_column(ForeignKey("treatment_records.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    record = relationship("TreatmentRecord", back_populates="evidence")
