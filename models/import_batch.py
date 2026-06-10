from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    scope_id: Mapped[int | None] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="osm")
    mode: Mapped[str] = mapped_column(String(64), nullable=False, default="dry_run")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_count: Mapped[int] = mapped_column(Integer, default=0)
    normalized_count: Mapped[int] = mapped_column(Integer, default=0)
    published_count: Mapped[int] = mapped_column(Integer, default=0)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="running", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    diff_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    rollback_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    protected_manual_overrides_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
