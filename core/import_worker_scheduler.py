"""Lightweight import-worker scheduler for admin queued jobs.

The standalone data/scripts/run_admin_import_worker.py remains supported, but
production web runtime also needs a deterministic consumer for jobs queued from
/admin/import-jobs actions. Without this loop, CityAdminImportJob rows can stay
in status=queued forever when no separate worker process is running.
"""

from __future__ import annotations

import asyncio
import logging
from asyncio import Task

from core.config import settings
from services.admin_city_import_tasks import run_queued_import_jobs

logger = logging.getLogger(__name__)
_task: Task[None] | None = None


def start_import_worker_scheduler() -> None:
    """Start polling queued admin import jobs when enabled.

    It is enabled explicitly by IMPORT_WORKER_SCHEDULER_ENABLED or implicitly in
    production so a deployed web process can consume jobs even if the separate
    import-worker daemon is not configured.
    """
    global _task
    enabled = bool(settings.import_worker_scheduler_enabled) or settings.app_env == "production"
    if not enabled or _task is not None:
        return
    _task = asyncio.create_task(_scheduler_loop())
    logger.info("import worker scheduler started")


async def stop_import_worker_scheduler() -> None:
    global _task
    task = _task
    _task = None
    if task is None:
        return
    task.cancel()
    await _await_cancelled(task)
    logger.info("import worker scheduler stopped")


async def _scheduler_loop() -> None:
    while True:
        await asyncio.to_thread(_run_once)
        await asyncio.sleep(max(5, int(settings.import_worker_scheduler_interval_seconds)))


async def _await_cancelled(task: Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        return


def _run_once() -> None:
    try:
        result = run_queued_import_jobs(
            actor_id="import-worker-scheduler",
            limit=max(1, int(settings.import_worker_scheduler_batch_limit)),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("import worker scheduler iteration failed: %s", exc)
        return
    queue = result.get("queue") if isinstance(result, dict) else None
    processed = result.get("processed") if isinstance(result, dict) else None
    failed = result.get("failed") if isinstance(result, dict) else None
    if processed or failed:
        logger.info("import worker scheduler processed=%s failed=%s queue=%s", processed, failed, queue)
