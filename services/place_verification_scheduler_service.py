from collections.abc import Callable, Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from schemas.place_verification import PlaceVerificationEnqueueSummary
from services.place_verification_service import enqueue_stale_places

SessionFactory = Callable[[], Session]
EnqueueFn = Callable[[Session, str], PlaceVerificationEnqueueSummary]


@dataclass(frozen=True)
class ScheduledVerificationResult:
    city_slug: str
    enqueued: int = 0
    already_pending: int = 0
    error: str | None = None


def parse_city_slugs(value: str, default_city_slug: str) -> tuple[str, ...]:
    parsed = tuple(filter(None, map(str.strip, value.split(","))))
    return parsed or (default_city_slug,)


def interval_hours_to_seconds(interval_hours: int) -> int:
    return max(interval_hours, 1) * 60 * 60


def run_scheduled_verification(
    session_factory: SessionFactory,
    city_slugs: Sequence[str],
    enqueue_fn: EnqueueFn = enqueue_stale_places,
) -> list[ScheduledVerificationResult]:
    return list(map(lambda slug: _run_city(session_factory, slug, enqueue_fn), city_slugs))


def _run_city(
    session_factory: SessionFactory,
    city_slug: str,
    enqueue_fn: EnqueueFn,
) -> ScheduledVerificationResult:
    db = session_factory()
    try:
        summary = enqueue_fn(db, city_slug)
        return ScheduledVerificationResult(
            city_slug=city_slug,
            enqueued=summary.enqueued,
            already_pending=summary.already_pending,
        )
    except Exception as exc:
        _rollback(db)
        return ScheduledVerificationResult(city_slug=city_slug, error=str(exc))
    finally:
        db.close()


def _rollback(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        return
