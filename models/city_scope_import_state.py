from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityScopeImportState(Base):
    __tablename__ = "city_scope_import_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    scope_id: Mapped[int] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="osm")
    import_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="tourist_core")
    last_successful_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    last_attempted_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str] = mapped_column(String(64), nullable=False, default="not_started")
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    last_raw_count: Mapped[int] = mapped_column(Integer, default=0)
    last_normalized_count: Mapped[int] = mapped_column(Integer, default=0)
    last_published_count: Mapped[int] = mapped_column(Integer, default=0)
    last_needs_review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    last_duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    last_missing_from_source_count: Mapped[int] = mapped_column(Integer, default=0)
    coverage_status: Mapped[str] = mapped_column(String(64), nullable=False, default="not_started")
    coverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
