from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Ward(Base):
    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    department_type: Mapped[str] = mapped_column(String(80), nullable=False, default="General")
    manager_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    facility = relationship("Facility", back_populates="wards", foreign_keys="[Ward.facility_id]")
    users = relationship("User", back_populates="ward", foreign_keys="[User.ward_id]")
    manager = relationship("User", back_populates="managed_ward", foreign_keys="[Ward.manager_user_id]")
