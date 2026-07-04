"""Read-model snapshots for admin and platform performance gates."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base

Json = JSONB().with_variant(JSON(), "sqlite")


class AdminOverviewSnapshot(Base):
    __tablename__ = "admin_overview_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payload: Mapped[dict[str, object]] = mapped_column(Json, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CityQualitySnapshot(Base):
    __tablename__ = "city_quality_snapshots"

    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), primary_key=True)
    readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    places_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_universe_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_review_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    auto_excluded_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    route_candidate_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    route_ready_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    route_blockers_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_blocker: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blockers: Mapped[dict[str, object]] = mapped_column(Json, nullable=False, default=dict)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    city = relationship("City", back_populates="quality_snapshots")


class BacklogQueueSnapshot(Base):
    __tablename__ = "backlog_queue_snapshots"
    __table_args__ = (
        UniqueConstraint("scope_type", "scope_id", "queue_code", "reason_code", name="uq_backlog_queue_snapshot_scope_queue_reason"),
        Index("ix_backlog_queue_snapshot_scope", "scope_type", "scope_id"),
        Index("ix_backlog_queue_snapshot_queue", "queue_code", "reason_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    queue_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sample_place_ids: Mapped[list[int]] = mapped_column(Json, nullable=False, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    stale_after: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
