from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ModuleBoundary(Base):
    """Registry of modular monolith boundaries."""

    __tablename__ = "module_boundaries"
    __table_args__ = (
        UniqueConstraint("module_code", name="uq_module_boundary_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_of_truth_tables: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    allowed_dependencies: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    emitted_events: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    consumed_events: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ExtractionCandidate(Base):
    """Candidate module for controlled service extraction."""

    __tablename__ = "extraction_candidates"
    __table_args__ = (
        UniqueConstraint("module_code", "target_service_name", name="uq_extraction_candidate_module_service"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    module_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    readiness_status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    api_contract_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    event_contract_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    data_migration_plan_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rollback_plan_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class IntegrationContract(Base):
    """Contract between modules or services."""

    __tablename__ = "integration_contracts"
    __table_args__ = (
        UniqueConstraint("producer", "consumer", "version", name="uq_integration_contract_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    producer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    consumer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_ref: Mapped[str] = mapped_column(String(1000), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    compatibility_policy: Mapped[str] = mapped_column(String(64), default="backward_compatible", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class StranglerAdapter(Base):
    """Adapter used during controlled extraction."""

    __tablename__ = "strangler_adapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_service: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    adapter_mode: Mapped[str] = mapped_column(String(64), default="shadow_read", nullable=False, index=True)
    read_strategy: Mapped[str] = mapped_column(String(255), nullable=False)
    write_strategy: Mapped[str] = mapped_column(String(255), nullable=False)
    fallback_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
