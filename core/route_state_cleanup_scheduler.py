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
_state = "stopped"


def start_route_state_cleanup_scheduler() -> None:
    global _state, _task, _thread_stop_event, _wake_event
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    # Ownership remains present throughout running and stopping. A restart is
    # permitted only after the previous scheduler task itself reaches done().
    if _task is not None:
        return

    _wake_event = asyncio.Event()
    _thread_stop_event = ThreadEvent()
    task = asyncio.create_task(_scheduler_loop(_wake_event, _thread_stop_event))
    _task = task
    _state = "running"
    task.add_done_callback(_finalize_scheduler_ownership)
    logger.info("route-state cleanup scheduler started")


async def stop_route_state_cleanup_scheduler() -> None:
    global _state
    task = _task
    wake_event = _wake_event
    thread_stop_event = _thread_stop_event
    if task is None:
        return

    _state = "stopping"
    if thread_stop_event is not None:
        thread_stop_event.set()
    if wake_event is not None:
        wake_event.set()

    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        # Cancellation of the owned scheduler task is normalized after its loop
        # has drained the active thread batch. Cancellation of this caller is
        # propagated, but ownership is deliberately retained until the task's
        # done callback runs, preventing stop/start overlap.
        if task.done() and task.cancelled():
            return
        raise


def _finalize_scheduler_ownership(task: Task[None]) -> None:
    global _active_batch, _state, _task, _thread_stop_event, _wake_event
    if _task is not task:
        return
    _task = None
    _wake_event = None
    _thread_stop_event = None
    _active_batch = None
    _state = "stopped"
    if task.cancelled():
        logger.info("route-state cleanup scheduler cancelled after drain")
    elif task.exception() is not None:
        logger.error(
            "route-state cleanup scheduler stopped with error",
            exc_info=(type(task.exception()), task.exception(), task.exception().__traceback__),
        )
    else:
        logger.info("route-state cleanup scheduler stopped")


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
