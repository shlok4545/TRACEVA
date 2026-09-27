from datetime import datetime, timezone

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False, default="Hospital", index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(150), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    users = relationship("User", back_populates="facility")
    wards = relationship("Ward", back_populates="facility")
    collector_profiles = relationship("CollectorProfile", back_populates="facility")
    pickup_requests = relationship("PickupRequest", back_populates="facility")
    incidents = relationship("Incident", back_populates="facility")
