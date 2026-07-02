from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class DestinationLaunchState(Base):
    """Current launch state for a city/destination."""

    __tablename__ = "destination_launch_states"
    __table_args__ = (
        UniqueConstraint("city_id", name="uq_destination_launch_state_city"),
        UniqueConstraint("destination_key", name="uq_destination_launch_state_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    destination_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    launch_status: Mapped[str] = mapped_column(String(64), default="created", nullable=False, index=True)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_route_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    state_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DestinationLaunchPipelineRun(Base):
    """One execution of the destination launch pipeline."""

    __tablename__ = "destination_launch_pipeline_runs"
    __table_args__ = (
        UniqueConstraint("pipeline_key", name="uq_destination_launch_pipeline_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    pipeline_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="queued", nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trigger_source: Mapped[str] = mapped_column(String(64), default="admin", nullable=False, index=True)
    processed_steps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_steps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_steps_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DestinationLaunchStep(Base):
    """One step inside a destination launch pipeline run."""

    __tablename__ = "destination_launch_steps"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "step_key", name="uq_destination_launch_step_run_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pipeline_run_id: Mapped[int] = mapped_column(ForeignKey("destination_launch_pipeline_runs.id"), nullable=False, index=True)
    step_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="queued", nullable=False, index=True)
    input_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    output_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DestinationLaunchChecklistItem(Base):
    """Persistent launch checklist item used by admin readiness UI."""

    __tablename__ = "destination_launch_checklist_items"
    __table_args__ = (
        UniqueConstraint("city_id", "item_code", name="uq_destination_launch_checklist_city_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(ForeignKey("destination_launch_pipeline_runs.id"), nullable=True, index=True)
    item_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False, index=True)
    is_required_for_live: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    evidence_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DestinationLaunchEvent(Base):
    """Append-only launch pipeline event for audit and timeline UI."""

    __tablename__ = "destination_launch_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(ForeignKey("destination_launch_pipeline_runs.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    next_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class DestinationReadinessSummary(Base):
    """Readiness snapshot for launch/publication/route readiness gates."""

    __tablename__ = "destination_readiness_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    pipeline_run_id: Mapped[int | None] = mapped_column(ForeignKey("destination_launch_pipeline_runs.id"), nullable=True, index=True)
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    places_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    places_publishable: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    places_route_eligible: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    photo_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    address_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hours_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    description_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duplicate_candidates_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conflict_candidates_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocking_issues: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    is_publishable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_route_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    search_projection_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    routing_projection_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
