from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.route_build_event import RouteBuildEvent


def record_route_build(
    route_or_db: object,
    route: object | None = None,
    *,
    source: str,
    latency_ms: int,
    city_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Persist analytics in an isolated transaction.

    The optional second positional argument preserves legacy ``(db, route)``
    callers, but the supplied caller Session is deliberately ignored. Route-state
    request sessions must never be committed or rolled back by analytics.
    """
    event_route = route_or_db if route is None else route
    db = SessionLocal()
    try:
        db.add(_event(event_route, source, latency_ms, city_id, user_id))
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        return False
    finally:
        db.close()


def _event(
    route: object,
    source: str,
    latency_ms: int,
    city_id: str | None,
    user_id: str | None,
) -> RouteBuildEvent:
    return RouteBuildEvent(
        route_id=str(getattr(route, "route_id", "")),
        user_id=user_id,
        source=source,
        city_id=city_id,
        total_places=int(getattr(route, "total_places", 0) or 0),
        total_minutes=int(getattr(route, "total_minutes", 0) or 0),
        quality_score=float(getattr(route, "quality_score", 0.0) or 0.0),
        warning_count=int(getattr(route, "warning_count", 0) or 0),
        has_warnings=bool(getattr(route, "has_warnings", False)),
        latency_ms=max(0, int(latency_ms)),
        warnings=list(getattr(route, "warnings", []) or []),
        quality_breakdown=dict(getattr(route, "quality_breakdown", {}) or {}),
    )


def route_analytics_summary(db: Session) -> dict[str, object]:
    events = db.query(RouteBuildEvent).all()
    total = len(events)
    return {
        "total_routes": total,
        "average_quality_score": _average(events, "quality_score"),
        "warning_rate": _rate(events, lambda event: bool(event.has_warnings)),
        "average_latency_ms": _average(events, "latency_ms"),
        "by_source": _by_source(events),
    }


def _average(events: list[RouteBuildEvent], field: str) -> float:
    values = list(map(lambda event: float(getattr(event, field, 0.0) or 0.0), events))
    return 0.0 if not values else round(sum(values) / len(values), 3)


def _rate(events: list[RouteBuildEvent], predicate: Callable[[RouteBuildEvent], bool]) -> float:
    if not events:
        return 0.0
    return round(sum(map(lambda event: 1 if predicate(event) else 0, events)) / len(events), 3)


def _by_source(events: list[RouteBuildEvent]) -> dict[str, int]:
    return dict(sorted(_reduce_sources(events).items()))


def _reduce_sources(events: list[RouteBuildEvent]) -> dict[str, int]:
    return {source: len(list(filter(lambda event: event.source == source, events))) for source in {e.source for e in events}}
