from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PlaceFactVersion(Base):
    """Versioned place fact.

    Stage 1 source-of-truth contract:
    import/AI create candidate facts; moderation/publication approve or reject them.
    """

    __tablename__ = "place_fact_versions"
    __table_args__ = (
        UniqueConstraint(
            "place_id",
            "field_name",
            "locale",
            "version",
            name="uq_place_fact_version_place_field_locale_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), default="default", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="candidate", nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False, index=True)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("place_fact_versions.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class AiTaskRun(Base):
    """One AI invocation with prompt, model, cost and output metadata."""

    __tablename__ = "ai_task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class AiCandidate(Base):
    """AI-proposed fact candidate.

    AI candidates are never approved/public facts by default.
    """

    __tablename__ = "ai_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ai_task_run_id: Mapped[int] = mapped_column(ForeignKey("ai_task_runs.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), default="default", nullable=False, index=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="candidate", nullable=False, index=True)
    place_fact_version_id: Mapped[int | None] = mapped_column(ForeignKey("place_fact_versions.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class ReviewDecision(Base):
    """Immutable moderation decision for candidates/facts/publication actions."""

    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False, index=True)
    previous_value_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    new_value_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    decision_metadata: Mapped[dict[str, object] | None] = mapped_column("metadata", JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class PublicationEvent(Base):
    """Append-only publication state transition."""

    __tablename__ = "publication_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    next_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    snapshot_version: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    is_replayed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
