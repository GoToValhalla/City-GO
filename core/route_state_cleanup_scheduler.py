from __future__ import annotations

import asyncio
import logging
import os
from asyncio import Task

from core.route_state_cleanup_runner import run_route_state_cleanup_once

logger = logging.getLogger(__name__)

ROUTE_STATE_CLEANUP_INTERVAL_SECONDS = 300
ROUTE_STATE_CLEANUP_BATCH_LIMIT = 1000
ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN = 10

_task: Task[None] | None = None


def start_route_state_cleanup_scheduler() -> None:
    global _task
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_scheduler_loop())
    logger.info("route-state cleanup scheduler started")


async def stop_route_state_cleanup_scheduler() -> None:
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
    logger.info("route-state cleanup scheduler stopped")


async def _scheduler_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(_run_bounded_cleanup)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("route-state cleanup scheduler iteration failed")
        await asyncio.sleep(ROUTE_STATE_CLEANUP_INTERVAL_SECONDS)


def _run_bounded_cleanup() -> int:
    deleted_total = 0
    for _ in range(ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN):
        deleted = run_route_state_cleanup_once(limit=ROUTE_STATE_CLEANUP_BATCH_LIMIT)
        deleted_total += deleted
        if deleted < ROUTE_STATE_CLEANUP_BATCH_LIMIT:
            break
    if deleted_total:
        logger.info("route-state cleanup scheduler deleted=%s", deleted_total)
    return deleted_total
