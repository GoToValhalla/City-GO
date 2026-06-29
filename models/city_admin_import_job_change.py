"""Persistent per-place change rows for admin import jobs."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityAdminImportJobChange(Base):
    __tablename__ = "city_admin_import_job_changes"
    __table_args__ = (
        Index("ix_import_job_changes_job_type", "job_id", "change_type"),
        Index("ix_import_job_changes_city_type", "city_id", "change_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("city_admin_import_jobs.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    external_source_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    place_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    before_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    after_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
