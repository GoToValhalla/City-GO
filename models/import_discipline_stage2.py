from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ImportRun(Base):
    """Stage 2 logical import execution.

    ImportRun owns operational import state. It must not be used as product publication state.
    """

    __tablename__ = "import_runs"
    __table_args__ = (
        UniqueConstraint("run_key", name="uq_import_run_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    scope_id: Mapped[int | None] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="osm", nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(64), default="city_import", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    checkpoint_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    quality_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ImportRunBatch(Base):
    """Stage 2 batch/page/chunk inside an ImportRun."""

    __tablename__ = "import_run_batches"
    __table_args__ = (
        UniqueConstraint("import_run_id", "batch_key", name="uq_import_run_batch_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_run_id: Mapped[int] = mapped_column(ForeignKey("import_runs.id"), nullable=False, index=True)
    batch_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_cursor: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    checkpoint_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ImportDeadLetterItem(Base):
    """Failed import payload that can be inspected and replayed."""

    __tablename__ = "import_dead_letter_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True, index=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_run_batches.id"), nullable=True, index=True)
    source_observation_id: Mapped[int | None] = mapped_column(ForeignKey("source_observations.id"), nullable=True, index=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    error_class: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    replay_status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    replay_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_replay_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ImportConflictCandidate(Base):
    """Reviewable import conflict/dedup candidate."""

    __tablename__ = "import_conflict_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), nullable=True, index=True)
    source_observation_id: Mapped[int] = mapped_column(ForeignKey("source_observations.id"), nullable=False, index=True)
    matched_place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conflict_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    evidence_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    resolution_status: Mapped[str] = mapped_column(String(32), default="open", nullable=False, index=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
