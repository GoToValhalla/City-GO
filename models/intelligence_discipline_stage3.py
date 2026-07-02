from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PromptVersion(Base):
    """Versioned prompt contract for enrichment tasks."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("task_type", "version", name="uq_prompt_version_task_version"),
        UniqueConstraint("prompt_hash", name="uq_prompt_version_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt_reference: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    rollout_policy: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    changelog: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class GoldenDataset(Base):
    """Versioned evaluation dataset for a task type."""

    __tablename__ = "golden_datasets"
    __table_args__ = (
        UniqueConstraint("task_type", "dataset_version", name="uq_golden_dataset_task_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), default="default", nullable=False, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    minimum_pass_rate: Mapped[float] = mapped_column(Float, default=0.95, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class EvaluationCase(Base):
    """One deterministic case inside a GoldenDataset."""

    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint("dataset_id", "case_key", name="uq_evaluation_case_dataset_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("golden_datasets.id"), nullable=False, index=True)
    case_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    input_payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    expected_output: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    expected_decision: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", nullable=False, index=True)
    tags: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RegressionGateRun(Base):
    """Prompt/model evaluation run against a golden dataset."""

    __tablename__ = "regression_gate_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prompt_version_id: Mapped[int] = mapped_column(ForeignKey("prompt_versions.id"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("golden_datasets.id"), nullable=False, index=True)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False, index=True)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    failed_cases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    failure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)


class CostBudgetPolicy(Base):
    """Cost and token budget by task, model and optional city."""

    __tablename__ = "cost_budget_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_provider: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    period: Mapped[str] = mapped_column(String(32), default="daily", nullable=False, index=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_cost_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_when_exceeded: Mapped[str] = mapped_column(String(32), default="block", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
