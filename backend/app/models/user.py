from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="WARD_STAFF", index=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True, index=True)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), onupdate=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    facility = relationship("Facility", back_populates="users", foreign_keys="[User.facility_id]")
    ward = relationship("Ward", back_populates="users", foreign_keys="[User.ward_id]")
    managed_ward = relationship("Ward", back_populates="manager", foreign_keys="[Ward.manager_user_id]")
    collector_profile = relationship("CollectorProfile", back_populates="user", uselist=False)
    reported_incidents = relationship("Incident", foreign_keys="[Incident.reported_by_user_id]", back_populates="reported_by")
    assigned_incidents = relationship("Incident", foreign_keys="[Incident.assigned_to_user_id]", back_populates="assigned_to")
