"""Durable poller for queued admin background operations."""

from __future__ import annotations

import asyncio
import logging
from asyncio import Task

from core.config import settings
from services.admin_background_operation_service import run_queued_background_operations

logger = logging.getLogger(__name__)
_task: Task[None] | None = None


def start_admin_background_operation_scheduler() -> None:
    global _task
    if not bool(settings.admin_background_operation_scheduler_enabled) or _task is not None:
        return
    _task = asyncio.create_task(_scheduler_loop())
    logger.info("admin background-operation scheduler started")


async def stop_admin_background_operation_scheduler() -> None:
    global _task
    task = _task
    _task = None
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("admin background-operation scheduler stopped")


async def _scheduler_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(
                run_queued_background_operations,
                limit=max(1, int(settings.admin_background_operation_scheduler_batch_limit)),
            )
        except Exception:  # noqa: BLE001
            logger.exception("admin background-operation scheduler iteration failed")
        await asyncio.sleep(max(2, int(settings.admin_background_operation_scheduler_interval_seconds)))
