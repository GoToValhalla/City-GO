"""Управляемая таксономия, качество данных и автоматические операции."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

Json = JSONB().with_variant(JSON(), "sqlite")


class TaxonomyMapping(Base):
    __tablename__ = "taxonomy_mappings"
    __table_args__ = (UniqueConstraint("source", "source_key", "source_value", "conditions_hash", name="uq_taxonomy_mapping_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    conditions: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    conditions_hash: Mapped[str] = mapped_column(String(64), default="-", nullable=False)
    fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TaxonomyDecision(Base):
    __tablename__ = "taxonomy_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    mapping_id: Mapped[int | None] = mapped_column(ForeignKey("taxonomy_mappings.id"), index=True)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(Json, default=list, nullable=False)
    alternatives: Mapped[list[dict[str, object]]] = mapped_column(Json, default=list, nullable=False)
    old_category_id: Mapped[int | None] = mapped_column(Integer)
    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    batch_id: Mapped[str | None] = mapped_column(String(64), index=True)
    reversible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TaxonomyConflict(Base):
    __tablename__ = "taxonomy_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(64), index=True)
    confidence: Mapped[float | None] = mapped_column(Float, index=True)
    current_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    recommended_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    details: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    resolution: Mapped[dict[str, object] | None] = mapped_column(Json)
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="warning", nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="place", nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    parameters: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    auto_fix_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocking_publication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocking_route_eligibility: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class QualityIssue(Base):
    __tablename__ = "quality_issues"
    __table_args__ = (UniqueConstraint("rule_id", "place_id", "fingerprint", name="uq_quality_issue_fingerprint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("quality_rules.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False, index=True)
    details: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TaxonomyBulkBatch(Base):
    __tablename__ = "taxonomy_bulk_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="preview", nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    filters: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    preview: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    result: Mapped[dict[str, object] | None] = mapped_column(Json)
    rollback_result: Mapped[dict[str, object] | None] = mapped_column(Json)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime)


class WorkflowOperation(Base):
    __tablename__ = "workflow_operations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    current_step: Mapped[str | None] = mapped_column(String(100))
    steps: Mapped[list[dict[str, object]]] = mapped_column(Json, default=list, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(Json, default=dict, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
