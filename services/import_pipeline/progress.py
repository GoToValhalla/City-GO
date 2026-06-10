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
