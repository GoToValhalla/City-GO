"""CITYGO-320: persistence and resume logic for tiled OSM import execution.

Pure CRUD/query helpers over models.import_tile_run.ImportTileRun — no
Overpass calls, no retry logic, no publication/review logic. The tiled
orchestrator (data/scripts/import_city_osm.py's tiled path, CITYGO-319)
is the only caller.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.import_tile_run import ImportTileRun
from services.osm_tile_planner import Tile

TERMINAL_STATUSES = ("completed", "failed", "skipped")


def ensure_tile_runs(
    db: Session,
    *,
    scope_id: int,
    city_admin_import_job_id: int | None,
    planner_version: str,
    tiles: tuple[Tile, ...],
) -> list[ImportTileRun]:
    """Idempotently ensures one ImportTileRun row exists per planned tile
    for this scope. Re-running the same plan (same deterministic tile_ids)
    against an existing set of rows never creates duplicates and never
    resets an already-terminal row's status — this is what makes resume
    safe: calling this again after a crash finds the same rows, with
    whatever status they were left in."""
    existing = {
        row.tile_id: row
        for row in db.query(ImportTileRun).filter(ImportTileRun.scope_id == scope_id).all()
    }
    result: list[ImportTileRun] = []
    for tile in tiles:
        row = existing.get(tile.tile_id)
        if row is None:
            row = ImportTileRun(
                scope_id=scope_id,
                city_admin_import_job_id=city_admin_import_job_id,
                tile_id=tile.tile_id,
                planner_version=planner_version,
                sequence=tile.sequence,
                total_tiles=tile.total_tiles,
                south=tile.south,
                west=tile.west,
                north=tile.north,
                east=tile.east,
                status="queued",
            )
            db.add(row)
            db.flush()
        result.append(row)
    result.sort(key=lambda row: row.sequence)
    return result


def next_unfinished_tile_run(rows: list[ImportTileRun]) -> ImportTileRun | None:
    """Resume point: the first (by sequence) row not already in a terminal
    state. Never restarts an already-completed tile."""
    for row in rows:
        if row.status not in TERMINAL_STATUSES:
            return row
    return None


def mark_tile_running(db: Session, row: ImportTileRun) -> None:
    row.status = "running"
    row.attempt_count += 1
    if row.started_at is None:
        row.started_at = datetime.utcnow()
    db.flush()


def mark_tile_completed(db: Session, row: ImportTileRun, *, batch_id: int | None, counters: dict[str, object] | None, retry_attempts: int) -> None:
    row.status = "completed"
    row.batch_id = batch_id
    row.counters = counters
    row.retry_attempts = retry_attempts
    row.failure_reason = None
    row.finished_at = datetime.utcnow()
    db.flush()


def mark_tile_failed(db: Session, row: ImportTileRun, *, failure_reason: str, retry_attempts: int, counters: dict[str, object] | None = None) -> None:
    row.status = "failed"
    row.failure_reason = failure_reason[:2000]
    row.retry_attempts = retry_attempts
    row.counters = counters
    row.finished_at = datetime.utcnow()
    db.flush()


def tile_progress_diagnostics(rows: list[ImportTileRun], *, started_at: datetime | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Truthful progress diagnostics (CITYGO-320 requirement): queued,
    running, completed, failed, skipped, remaining, total progress %,
    elapsed time, ETA if calculable. Every count is read directly from
    already-persisted rows — nothing here is estimated from timing alone."""
    total = len(rows)
    by_status: dict[str, int] = {"queued": 0, "running": 0, "completed": 0, "failed": 0, "skipped": 0}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1

    finished = by_status["completed"] + by_status["failed"] + by_status["skipped"]
    remaining = total - finished
    progress_pct = round((finished / total) * 100.0, 2) if total else 0.0

    elapsed_seconds: float | None = None
    eta_seconds: float | None = None
    if started_at is not None:
        current = now or datetime.utcnow()
        elapsed_seconds = (current - started_at).total_seconds()
        # ETA is only calculable when at least one tile has genuinely
        # finished — extrapolating a rate from zero completed tiles would
        # be a fabricated estimate, not a truthful one.
        if finished > 0 and remaining > 0 and elapsed_seconds > 0:
            average_seconds_per_tile = elapsed_seconds / finished
            eta_seconds = round(average_seconds_per_tile * remaining, 2)

    return {
        "total_tiles": total,
        "queued": by_status["queued"],
        "running": by_status["running"],
        "completed": by_status["completed"],
        "failed": by_status["failed"],
        "skipped": by_status["skipped"],
        "remaining": remaining,
        "total_progress_pct": progress_pct,
        "elapsed_seconds": elapsed_seconds,
        "eta_seconds": eta_seconds,
    }


def reset_scope_tile_runs(db: Session, *, scope_id: int) -> int:
    """Explicit, deliberate reset (NOT called by the normal resume path) —
    only for an operator who wants to force a full re-run of a scope's
    tiles from scratch. Returns the number of rows deleted."""
    count = db.query(ImportTileRun).filter(ImportTileRun.scope_id == scope_id).count()
    db.query(ImportTileRun).filter(ImportTileRun.scope_id == scope_id).delete()
    db.flush()
    return count
