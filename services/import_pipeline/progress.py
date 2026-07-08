"""Обновление прогресса import job."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.city_admin_import_job import CityAdminImportJob
from services.import_pipeline.steps import STEP_LABELS


def set_step(
    job: CityAdminImportJob,
    step: str,
    *,
    total: int | None = None,
    processed: int | None = None,
    successful: int | None = None,
    failed: int | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    job.current_step = step
    job.updated_at = datetime.utcnow()
    if total is not None:
        job.total_items = total
    if processed is not None:
        job.processed_items = processed
    if successful is not None:
        job.successful_items = successful
    if failed is not None:
        job.failed_items = failed
    if detail is not None:
        base = dict(job.step_details or {})
        base.update(detail)
        job.step_details = base


def touch_progress(job: CityAdminImportJob, *, processed: int | None = None) -> None:
    """Heartbeat for long per-item loops: bump updated_at/processed_items without
    changing current_step, so admins polling the job see it is still alive mid-step."""
    job.updated_at = datetime.utcnow()
    if processed is not None:
        job.processed_items = processed


def set_current_scope(job: CityAdminImportJob, *, scope_code: str, scope_name: str | None = None) -> None:
    """Record which scope collecting_places is working on right now, plus a
    step_started_at timestamp, so admins can see not just "collecting_places"
    but which scope and how long this specific scope has been running."""
    details = dict(job.step_details or {})
    details["current_scope_code"] = scope_code
    details["current_scope_name"] = scope_name
    details["step_started_at"] = datetime.utcnow().isoformat()
    job.step_details = details
    job.updated_at = datetime.utcnow()


def append_step_warning(job: CityAdminImportJob, step: str, error: object, *, extra: dict[str, Any] | None = None) -> None:
    details = dict(job.step_details or {})
    warnings = list(details.get("warnings") or [])
    warning = {"step": step, "error": str(error)[:1000]}
    if extra:
        warning.update(extra)
    warnings.append(warning)
    details["warnings"] = warnings
    job.step_details = details
    job.last_error = job.last_error or f"{step}: {str(error)[:500]}"
    job.updated_at = datetime.utcnow()


def step_label(step: str | None) -> str:
    if not step:
        return "—"
    return STEP_LABELS.get(step, step)


def is_stalled(job: CityAdminImportJob, *, now: datetime | None = None) -> bool:
    from services.import_pipeline.steps import STALL_THRESHOLD_MINUTES, TERMINAL_STEPS

    if job.current_step in TERMINAL_STEPS or job.status in {"success", "failed", "cancelled"}:
        return False
    ref = job.updated_at or job.started_at or job.created_at
    if ref is None:
        return False
    current = now or datetime.utcnow()
    return (current - ref).total_seconds() > STALL_THRESHOLD_MINUTES * 60


def worker_progress_snapshot(job: CityAdminImportJob | None, *, now: datetime | None = None) -> dict[str, Any] | None:
    """Cheap, query-free diagnostic view of a running/queued job for admin polling.

    Reuses existing fields only: current_step, updated_at (as heartbeat),
    started_at, step_details["current_scope_code"/"current_scope_name"/"step_started_at"].
    No DB access here — the caller already has `job` loaded.
    """
    from services.import_pipeline.steps import STALL_THRESHOLD_MINUTES

    if job is None or job.status not in {"queued", "running"}:
        return None
    current = now or datetime.utcnow()
    details = dict(job.step_details or {})
    stale_after_seconds = STALL_THRESHOLD_MINUTES * 60
    last_heartbeat_at = job.updated_at or job.started_at or job.created_at
    running_for_seconds = int((current - job.started_at).total_seconds()) if job.started_at else None
    step_started_raw = details.get("step_started_at")
    step_started_at = _parse_iso(step_started_raw) if isinstance(step_started_raw, str) else None
    step_reference = step_started_at or job.started_at
    current_step_running_for_seconds = int((current - step_reference).total_seconds()) if step_reference else None
    stale = is_stalled(job, now=current)
    return {
        "current_step": job.current_step,
        "current_scope_code": details.get("current_scope_code"),
        "current_scope_name": details.get("current_scope_name"),
        "step_started_at": step_started_at.isoformat() if step_started_at else None,
        "last_heartbeat_at": last_heartbeat_at.isoformat() if last_heartbeat_at else None,
        "running_for_seconds": running_for_seconds,
        "current_step_running_for_seconds": current_step_running_for_seconds,
        "stale_after_seconds": stale_after_seconds,
        "is_stale": stale,
        "admin_hint": _progress_admin_hint(job, stale=stale, scope_code=details.get("current_scope_code")),
    }


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _progress_admin_hint(job: CityAdminImportJob, *, stale: bool, scope_code: str | None) -> str:
    if stale:
        return "Воркер не обновлял прогресс дольше порога — возможен стопор, проверьте логи backend."
    step = step_label(job.current_step)
    if scope_code:
        return f"Воркер активен: шаг «{step}», скоуп «{scope_code}»."
    return f"Воркер активен: шаг «{step}»."
