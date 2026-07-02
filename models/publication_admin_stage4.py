from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PublicationTransitionRule(Base):
    """Allowed public state transition contract."""

    __tablename__ = "publication_transition_rules"
    __table_args__ = (
        UniqueConstraint("entity_type", "from_state", "to_state", name="uq_publication_transition_rule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    from_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    required_role: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    required_quality_gate: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_destructive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class QualityGateRule(Base):
    """Publication quality gate rule."""

    __tablename__ = "quality_gate_rules"
    __table_args__ = (
        UniqueConstraint("gate_code", name="uq_quality_gate_rule_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gate_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operator: Mapped[str] = mapped_column(String(16), nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="blocker", nullable=False, index=True)
    failure_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RollbackRequest(Base):
    """Explicit rollback intent for public state."""

    __tablename__ = "rollback_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False, index=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class AdminBulkOperation(Base):
    """Bulk admin operation with dry-run/apply contract."""

    __tablename__ = "admin_bulk_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_filter: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="dry_run", nullable=False, index=True)
    dry_run_operation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    affected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class AdminKillSwitch(Base):
    """Operation freeze contract for high-risk admin actions."""

    __tablename__ = "admin_kill_switches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    switch_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
