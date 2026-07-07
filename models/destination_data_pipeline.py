"""Destination-owned data pipeline run state."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base
from models.destination import Destination  # noqa: F401


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DestinationDataPipelineRun(Base):
    __tablename__ = "destination_data_pipeline_runs"
    __table_args__ = (
        UniqueConstraint("destination_id", "idempotency_key", name="uq_destination_pipeline_idempotency"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False, default="admin")
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="admin_workspace")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="preparing", index=True)
    scope_ids: Mapped[list[int]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counters: Mapped[dict[str, int]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=dict)
    errors: Mapped[list[dict[str, object]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="full", index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    destination = relationship("Destination")
