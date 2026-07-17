from __future__ import annotations

import asyncio
import logging
import os
from asyncio import Event, Task

from core.route_state_cleanup_runner import run_route_state_cleanup_once

logger = logging.getLogger(__name__)

ROUTE_STATE_CLEANUP_INTERVAL_SECONDS = 300
ROUTE_STATE_CLEANUP_BATCH_LIMIT = 1000
ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN = 10

_task: Task[None] | None = None
_stop_event: Event | None = None


def start_route_state_cleanup_scheduler() -> None:
    global _stop_event, _task
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if _task is not None and not _task.done():
        return
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_scheduler_loop(_stop_event))
    logger.info("route-state cleanup scheduler started")


async def stop_route_state_cleanup_scheduler() -> None:
    global _stop_event, _task
    task = _task
    stop_event = _stop_event
    _task = None
    _stop_event = None
    if task is None:
        return
    if stop_event is not None:
        stop_event.set()
    try:
        await task
    except asyncio.CancelledError:
        # Defensive fallback for external task cancellation. Normal application
        # shutdown is cooperative and waits for the active cleanup batch.
        pass
    logger.info("route-state cleanup scheduler stopped")


async def _scheduler_loop(stop_event: Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(_run_bounded_cleanup, stop_event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("route-state cleanup scheduler iteration failed")
        if stop_event.is_set():
            break
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=ROUTE_STATE_CLEANUP_INTERVAL_SECONDS,
            )
        except TimeoutError:
            continue


def _run_bounded_cleanup(stop_event: Event | None = None) -> int:
    deleted_total = 0
    for _ in range(ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN):
        if stop_event is not None and stop_event.is_set():
            break
        deleted = run_route_state_cleanup_once(limit=ROUTE_STATE_CLEANUP_BATCH_LIMIT)
        deleted_total += deleted
        if deleted < ROUTE_STATE_CLEANUP_BATCH_LIMIT:
            break
    if deleted_total:
        logger.info("route-state cleanup scheduler deleted=%s", deleted_total)
    return deleted_total
