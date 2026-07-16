"""CITYGO-320: persistent per-tile execution state for tiled OSM imports.

One row per (scope, tile_id) — the durable source of truth for resume:
which tiles are queued/running/completed/failed/skipped for a given
scope's tiled import plan. tile_id is deterministic (services/
osm_tile_planner.py), so re-planning the same bbox/config always maps
back to the same rows — a resumed run finds its own prior progress by
tile_id, never by row order or timing.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class ImportTileRun(Base):
    __tablename__ = "import_tile_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope_id: Mapped[int] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=False, index=True)
    city_admin_import_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True, index=True)

    tile_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    planner_version: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tiles: Mapped[int] = mapped_column(Integer, nullable=False)

    south: Mapped[float] = mapped_column(Float, nullable=False)
    west: Mapped[float] = mapped_column(Float, nullable=False)
    north: Mapped[float] = mapped_column(Float, nullable=False)
    east: Mapped[float] = mapped_column(Float, nullable=False)

    # queued -> running -> completed | failed | skipped
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    counters: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
