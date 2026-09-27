from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class WastePassport(Base):
    __tablename__ = "waste_passports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    passport_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    generated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    risk_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW", index=True)
    total_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    qr_token: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    qr_generated_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    items = relationship("WastePassportItem", back_populates="passport", cascade="all, delete-orphan")
    events = relationship("WastePassportEvent", back_populates="passport", cascade="all, delete-orphan")
    pickup_requests = relationship("PickupRequest", back_populates="passport", cascade="all, delete-orphan")
    transport_events = relationship("TransportEvent", back_populates="passport", cascade="all, delete-orphan")
    treatment_records = relationship("TreatmentRecord", back_populates="passport", cascade="all, delete-orphan")


class WastePassportItem(Base):
    __tablename__ = "waste_passport_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    item_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contamination_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category: Mapped[str | None] = mapped_column(String(150), nullable=True)
    segregation_group: Mapped[str | None] = mapped_column(String(150), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    requires_human_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    classification_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    passport = relationship("WastePassport", back_populates="items")


class WastePassportEvent(Base):
    __tablename__ = "waste_passport_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    passport_id: Mapped[int] = mapped_column(ForeignKey("waste_passports.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    passport = relationship("WastePassport", back_populates="events")


class WasteCategory(Base):
    __tablename__ = "waste_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    segregation_group: Mapped[str] = mapped_column(String(120), nullable=False, default="General")
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False, default="MEDIUM", index=True)
    default_disposal_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    handling_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    rules = relationship("WasteRule", back_populates="category")
    risk_assessments = relationship("RiskAssessment", back_populates="category")


class WasteRule(Base):
    __tablename__ = "waste_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("waste_categories.id"), nullable=False, index=True)
    item_keyword: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    item_pattern: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    risk_modifier: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    handling_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    category = relationship("WasteCategory", back_populates="rules")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("waste_categories.id"), nullable=False, index=True)
    base_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    waiting_time_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quantity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    handling_condition_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    incident_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW", index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    category = relationship("WasteCategory", back_populates="risk_assessments")
