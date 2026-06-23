from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.bot_event import BotEvent


def get_bot_analytics_summary(db: Session, *, days: int = 7) -> dict[str, Any]:
    """Return compact operational/product analytics for the Telegram bot admin screen."""

    normalized_days = max(1, min(int(days), 90))
    cutoff = datetime.utcnow() - timedelta(days=normalized_days)
    base_query = db.query(BotEvent).filter(BotEvent.created_at >= cutoff)

    started = _event_count(base_query, "route_started")
    completed = _event_count(base_query, "route_completed")
    completion_rate = round((completed / started) * 100, 1) if started else 0.0

    no_result_events = (
        base_query.filter(BotEvent.event_type == "search_no_results")
        .order_by(BotEvent.created_at.desc())
        .limit(20)
        .all()
    )

    latest_events = base_query.order_by(BotEvent.created_at.desc()).limit(20).all()

    return {
        "window_days": normalized_days,
        "active_users": _scalar_int(
            base_query.with_entities(func.count(func.distinct(BotEvent.telegram_user_id))).scalar()
        ),
        "events_total": base_query.count(),
        "events_by_type": _count_rows(
            base_query.with_entities(BotEvent.event_type, func.count(BotEvent.id))
            .group_by(BotEvent.event_type)
            .order_by(func.count(BotEvent.id).desc())
            .all()
        ),
        "top_cities": _count_rows(
            base_query.filter(BotEvent.city_slug.isnot(None))
            .with_entities(BotEvent.city_slug, func.count(BotEvent.id))
            .group_by(BotEvent.city_slug)
            .order_by(func.count(BotEvent.id).desc())
            .limit(10)
            .all()
        ),
        "route_funnel": {
            "started": started,
            "completed": completed,
            "completion_rate_percent": completion_rate,
        },
        "search_no_results": [
            {
                "query": _payload_value(event.payload, "query"),
                "city_slug": event.city_slug,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in no_result_events
        ],
        "latest_events": [
            {
                "event_type": event.event_type,
                "telegram_user_id": event.telegram_user_id,
                "city_slug": event.city_slug,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in latest_events
        ],
    }


def _event_count(query, event_type: str) -> int:
    return query.filter(BotEvent.event_type == event_type).count()


def _count_rows(rows: list[tuple[Any, int]]) -> list[dict[str, Any]]:
    return [{"key": str(key), "count": _scalar_int(count)} for key, count in rows if key is not None]


def _payload_value(payload: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _scalar_int(value: Any) -> int:
    return int(value or 0)
