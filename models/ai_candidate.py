"""AI task audit trail and review candidates."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class AITaskRun(Base):
    __tablename__ = "ai_task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="created", index=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")

    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="admin", index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    review_queue_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_queue_items.id"),
        nullable=True,
        index=True,
    )
    budget_reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_budget_reservations.id"),
        nullable=True,
        index=True,
    )

    input_tokens_estimate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    prompt_snapshot: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    output_snapshot: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AICandidate(Base):
    __tablename__ = "ai_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_run_id: Mapped[int] = mapped_column(ForeignKey("ai_task_runs.id"), nullable=False, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    review_queue_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("review_queue_items.id"),
        nullable=True,
        index=True,
    )
    candidate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    proposed_payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    evidence_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="ai")
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
