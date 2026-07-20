from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base

_json = JSONB().with_variant(JSON(), "sqlite")


class RouteSession(Base):
    __tablename__ = "route_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False, index=True)
    user_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ownership_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    current_point_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    visited_point_indexes: Mapped[list[int]] = mapped_column(_json, default=list, nullable=False)
    skipped_point_indexes: Mapped[list[int]] = mapped_column(_json, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    route = relationship("Route")
    points = relationship(
        "RouteSessionPoint",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="RouteSessionPoint.ordering_index",
    )


class RouteSessionPoint(Base):
    __tablename__ = "route_session_points"
    __table_args__ = (
        UniqueConstraint("session_id", "ordering_index", name="uq_route_session_point_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("route_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    ordering_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_visited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    visited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("RouteSession", back_populates="points")
