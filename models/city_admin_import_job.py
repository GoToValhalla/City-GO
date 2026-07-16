"""Задача импорта города, созданная через админку.

Immutable lifecycle (fix for the production Job #1 corruption — a terminal
row silently reused across separate worker runs, mixing timelines/counters
from unrelated executions): one admin launch or retry always inserts a NEW
row; an existing row is NEVER reset back to queued/running once it reaches
a terminal status. A retry's new row points at the row it replaces via
previous_job_id, forming an append-only retry chain per city. See
services/admin_city_import_job_service.py for the enqueue/retry/claim
logic that enforces this.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityAdminImportJob(Base):
    __tablename__ = "city_admin_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    # Points at the row this one retries, forming an append-only retry
    # chain. NULL for the first launch of a city. Never mutated after
    # creation, never points at a row that isn't itself a genuine prior
    # CityAdminImportJob for the same city.
    previous_job_id: Mapped[int | None] = mapped_column(ForeignKey("city_admin_import_jobs.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="admin_city_import")
    scopes_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scopes_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    places_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    places_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    step_details: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Set only by the legacy-repair command (data/scripts/repair_import_job_lifecycle.py)
    # when a terminal row is found reset back to queued/running by the OLD,
    # now-removed reuse logic and cannot be safely reconstructed into a
    # truthful terminal state. Never set by normal enqueue/claim/transition
    # code paths.
    lifecycle_flag: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
