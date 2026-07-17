from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

_json = JSONB().with_variant(JSON(), "sqlite")


class UserRouteStateRegistry(Base):
    __tablename__ = "user_route_state_registry"
    __table_args__ = (
        Index(
            "ix_user_route_state_registry_expires_at_route_id",
            "expires_at",
            "route_id",
        ),
    )

    route_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    place_ids: Mapped[list[int]] = mapped_column(_json, nullable=False, default=list)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(hours=24),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
