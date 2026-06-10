"""Feature toggles: global, city, place, module scopes."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class FeatureToggle(Base):
    __tablename__ = "feature_toggles"
    __table_args__ = (UniqueConstraint("scope", "scope_id", "key", name="uq_feature_toggle_scope_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value_bool: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
