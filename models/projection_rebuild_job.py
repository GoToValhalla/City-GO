from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ProjectionRebuildJob(Base):
    """Authoritative execution and readiness generation record."""

    __tablename__ = "projection_rebuild_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    projection_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    scope_key: Mapped[str] = mapped_column(String(64), default="global", nullable=False, index=True)
    generation: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_snapshot_version: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    expected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rebuilt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_context: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
