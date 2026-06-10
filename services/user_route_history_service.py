from sqlalchemy.orm import Session

from models.route_build_event import RouteBuildEvent


def user_route_history(db: Session, user_id: str, limit: int = 20) -> list[dict[str, object]]:
    events = (
        db.query(RouteBuildEvent)
        .filter(RouteBuildEvent.user_id == user_id)
        .order_by(RouteBuildEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(map(_history_item, events))


def _history_item(event: RouteBuildEvent) -> dict[str, object]:
    return {
        "route_id": event.route_id,
        "source": event.source,
        "city_id": event.city_id,
        "total_places": event.total_places,
        "quality_score": event.quality_score,
        "warning_count": event.warning_count,
        "created_at": event.created_at,
    }
