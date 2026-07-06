"""Region-first destination discovery jobs and candidates."""

from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DestinationDiscoveryJob(Base):
    __tablename__ = "destination_discovery_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    region_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic")
    region_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    options: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DestinationDiscoveryCandidate(Base):
    __tablename__ = "destination_discovery_candidates"
    __table_args__ = (UniqueConstraint("job_id", "external_id", name="uq_discovery_job_external"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("destination_discovery_jobs.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    english_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False, default="city")
    parent_region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    polygon_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    warnings_json: Mapped[list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    existing_match_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    scope_overlaps_json: Mapped[list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    recommended_scopes_json: Mapped[list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    reasons_json: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_destination_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
