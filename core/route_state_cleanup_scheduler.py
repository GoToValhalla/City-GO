from __future__ import annotations

import asyncio
import logging
import os
from asyncio import Event, Task
from threading import Event as ThreadEvent

from core.route_state_cleanup_runner import run_route_state_cleanup_once

logger = logging.getLogger(__name__)

ROUTE_STATE_CLEANUP_INTERVAL_SECONDS = 300
ROUTE_STATE_CLEANUP_BATCH_LIMIT = 1000
ROUTE_STATE_CLEANUP_MAX_BATCHES_PER_RUN = 10

_task: Task[None] | None = None
_wake_event: Event | None = None
_thread_stop_event: ThreadEvent | None = None
_active_batch: Task[int] | None = None


def start_route_state_cleanup_scheduler() -> None:
    global _task, _thread_stop_event, _wake_event
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if _task is not None and not _task.done():
        return
    _wake_event = asyncio.Event()
    _thread_stop_event = ThreadEvent()
    _task = asyncio.create_task(_scheduler_loop(_wake_event, _thread_stop_event))
    logger.info("route-state cleanup scheduler started")


async def stop_route_state_cleanup_scheduler() -> None:
    global _active_batch, _task, _thread_stop_event, _wake_event
    task = _task
    wake_event = _wake_event
    thread_stop_event = _thread_stop_event
    if task is None:
        return

    if thread_stop_event is not None:
        thread_stop_event.set()
    if wake_event is not None:
        wake_event.set()

    caller_cancelled = False
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        # If the owned scheduler task was cancelled externally, its loop has
        # already drained the active thread batch in its finally block. Normalize
        # that terminal state so application shutdown can continue. If this stop
        # coroutine itself was cancelled, preserve the caller cancellation after
        # owned work is drained.
        caller_cancelled = not task.cancelled()
    finally:
        batch = _active_batch
        if batch is not None and not batch.done():
            try:
                await asyncio.shield(batch)
            except asyncio.CancelledError:
                caller_cancelled = True
        if _task is task:
            _task = None
            _wake_event = None
            _thread_stop_event = None
            _active_batch = None

    logger.info("route-state cleanup scheduler stopped")
    if caller_cancelled:
        raise asyncio.CancelledError


async def _scheduler_loop(wake_event: Event, thread_stop_event: ThreadEvent) -> None:
    global _active_batch
    try:
        while not thread_stop_event.is_set():
            batch = asyncio.create_task(asyncio.to_thread(_run_bounded_cleanup, thread_stop_event))
            _active_batch = batch
            try:
                await asyncio.shield(batch)
            except asyncio.CancelledError:
                thread_stop_event.set()
                wake_event.set()
                await asyncio.shield(batch)
                raise
            except Exception:
                logger.exception("route-state cleanup scheduler iteration failed")
            finally:
                if _active_batch is batch and batch.done():
                    _active_batch = None

            if thread_stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    wake_event.wait(),
                    timeout=ROUTE_STATE_CLEANUP_INTERVAL_SECONDS,
                )
            except TimeoutError:
                continue
    finally:
        batch = _active_batch
        if batch is not None and not batch.done():
            thread_stop_event.set()
            await asyncio.shield(batch)


def _run_bounded_cleanup(stop_event: ThreadEvent | None = None) -> int:
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
