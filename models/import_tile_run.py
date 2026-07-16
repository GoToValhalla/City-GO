"""CITYGO-320/CITYGO-338: persistent per-execution, per-tile state for
tiled OSM imports.

One row per (execution_id, tile_id) — the durable source of truth for
resume: which tiles are queued/running/completed/failed/skipped for one
specific tiled import EXECUTION. tile_id is deterministic (services/
osm_tile_planner.py), so re-planning the same bbox/config within the same
execution always maps back to the same rows.

execution_id (CITYGO-338) is the identity boundary a resume must respect:
- Restarting the SAME execution (same execution_id — e.g. retrying the
  same CityAdminImportJob, which keeps the same job.id across retries)
  finds its own prior rows via (execution_id, tile_id) and resumes from
  the first unfinished tile.
- A NEW execution (a fresh execution_id — a brand-new import job, or a
  CLI run with no job) always creates fresh rows for every tile and
  processes all of them, even if an older execution for the same scope
  already completed some tiles at the same coordinates. Old executions'
  rows are never deleted or reused — they remain as history.
- Two concurrent executions (e.g. two overlapping worker runs) never
  collide or share checkpoints, because their execution_ids differ.

scope_id is kept as a non-unique index for cross-execution history
queries (e.g. "show me every execution this scope has ever run"); it is
no longer part of the uniqueness/resume key.
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
    execution_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
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
