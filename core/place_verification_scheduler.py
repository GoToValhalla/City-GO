import asyncio
import logging
from asyncio import Task

from core.config import settings
from db.session import SessionLocal
from services.feature_toggle_service import is_toggle_enabled
from services.place_verification_scheduler_service import (
    ScheduledVerificationResult,
    interval_hours_to_seconds,
    parse_city_slugs,
    run_scheduled_verification,
)

logger = logging.getLogger(__name__)
_task: Task[None] | None = None


def start_place_verification_scheduler() -> None:
    global _task
    if not settings.verification_scheduler_enabled or _task is not None:
        return
    _task = asyncio.create_task(_scheduler_loop())


async def stop_place_verification_scheduler() -> None:
    global _task
    task = _task
    _task = None
    if task is None:
        return
    task.cancel()
    await _await_cancelled(task)


async def _scheduler_loop() -> None:
    while True:
        await asyncio.to_thread(_run_once)
        await asyncio.sleep(interval_hours_to_seconds(settings.verification_scheduler_interval_hours))


async def _await_cancelled(task: Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        return


def _run_once() -> None:
    db = SessionLocal()
    try:
        if not is_toggle_enabled(db, "place_verification_enabled", default=True):
            return
    finally:
        db.close()
    slugs = parse_city_slugs(
        settings.verification_scheduler_city_slugs,
        settings.default_city_slug,
    )
    tuple(map(_log_result, run_scheduled_verification(SessionLocal, slugs)))


def _log_result(result: ScheduledVerificationResult) -> None:
    if result.error is not None:
        logger.warning("place verification scheduler failed: %s", result)
        return
    logger.info("place verification scheduler enqueued stale places: %s", result)
