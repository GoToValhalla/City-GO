from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from models.route import Route
from models.route_place import RoutePlace
from models.route_session import RouteSession, RouteSessionPoint

_ALLOWED_PUBLICATION_STATUSES = {"published", "auto_published", "limited_published"}
_BLOCKED_ROUTE_CATEGORIES = {
    "service",
    "bank",
    "atm",
    "mvd",
    "police",
    "government",
    "transport",
    "hospital",
    "health",
    "medical",
    "pharmacy",
    "military",
    "cemetery",
    "industrial",
    "waste_disposal",
    "fuel",
    "parking",
    "car_service",
}
_TERMINAL_STATUSES = {"completed", "abandoned"}


class RouteSessionError(ValueError):
    pass


class RouteSessionNotFound(RouteSessionError):
    pass


class RouteSessionConflict(RouteSessionError):
    pass


class RouteSessionUnavailable(RouteSessionError):
    pass


def start_route_session(db: Session, route_id: int, user_key: str | None = None) -> RouteSession:
    route = _get_route_with_points(db, route_id)
    if route is None or not route.is_active:
        raise RouteSessionNotFound("route_not_found")

    eligible_points = _eligible_route_points(route)
    if len(eligible_points) < 2:
        raise RouteSessionUnavailable("route_has_less_than_two_eligible_points")

    session = RouteSession(route_id=route.id, user_key=user_key, status="active", current_point_index=0)
    db.add(session)
    db.flush()

    for index, route_place in enumerate(eligible_points):
        place = route_place.place
        db.add(
            RouteSessionPoint(
                session_id=session.id,
                place_id=route_place.place_id,
                ordering_index=index,
                title=place.title if place else None,
                lat=place.lat if place else None,
                lng=place.lng if place else None,
            )
        )

    db.commit()
    return get_route_session(db, session.id)


def get_route_session(db: Session, session_id: int) -> RouteSession:
    session = (
        db.query(RouteSession)
        .options(joinedload(RouteSession.points))
        .filter(RouteSession.id == session_id)
        .first()
    )
    if session is None:
        raise RouteSessionNotFound("route_session_not_found")
    session.points = sorted(session.points, key=lambda item: item.ordering_index)
    return session


def update_route_session(
    db: Session,
    session_id: int,
    *,
    status: str | None = None,
    current_point_index: int | None = None,
) -> RouteSession:
    session = get_route_session(db, session_id)
    if session.status in _TERMINAL_STATUSES:
        raise RouteSessionConflict("route_session_is_terminal")

    if status is not None:
        if status == "paused":
            session.paused_at = datetime.utcnow()
        elif status == "active":
            session.paused_at = None
        elif status == "abandoned":
            session.completed_at = None
        session.status = status

    if current_point_index is not None:
        if current_point_index >= len(session.points):
            raise RouteSessionConflict("current_point_index_out_of_range")
        session.current_point_index = current_point_index

    session.updated_at = datetime.utcnow()
    db.commit()
    return get_route_session(db, session_id)


def check_in_route_point(db: Session, session_id: int, point_index: int, action: str) -> RouteSession:
    session = get_route_session(db, session_id)
    if session.status in _TERMINAL_STATUSES:
        raise RouteSessionConflict("route_session_is_terminal")
    if point_index >= len(session.points):
        raise RouteSessionConflict("point_index_out_of_range")

    point = session.points[point_index]
    now = datetime.utcnow()
    visited = set(_json_indexes(session.visited_point_indexes))
    skipped = set(_json_indexes(session.skipped_point_indexes))

    if action == "visit":
        point.is_visited = True
        point.is_skipped = False
        point.visited_at = now
        point.skipped_at = None
        visited.add(point_index)
        skipped.discard(point_index)
    elif action == "skip":
        point.is_skipped = True
        point.is_visited = False
        point.skipped_at = now
        point.visited_at = None
        skipped.add(point_index)
        visited.discard(point_index)
    else:
        raise RouteSessionConflict("unsupported_point_action")

    session.visited_point_indexes = sorted(visited)
    session.skipped_point_indexes = sorted(skipped)
    session.current_point_index = _next_open_index(len(session.points), visited | skipped)
    session.status = "completed" if session.current_point_index >= len(session.points) else "active"
    if session.status == "completed":
        session.completed_at = now
    session.updated_at = now

    db.commit()
    return get_route_session(db, session_id)


def complete_route_session(db: Session, session_id: int) -> RouteSession:
    session = get_route_session(db, session_id)
    if session.status == "abandoned":
        raise RouteSessionConflict("route_session_is_abandoned")
    now = datetime.utcnow()
    session.status = "completed"
    session.current_point_index = len(session.points)
    session.completed_at = session.completed_at or now
    session.updated_at = now
    db.commit()
    return get_route_session(db, session_id)


def _get_route_with_points(db: Session, route_id: int) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.id == route_id)
        .first()
    )
    if route is None:
        return None
    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


def _eligible_route_points(route: Route) -> list[RoutePlace]:
    return [route_place for route_place in route.route_places if _is_route_place_eligible(route_place)]


def _is_route_place_eligible(route_place: RoutePlace) -> bool:
    place = route_place.place
    if place is None:
        return False
    category = (place.canonical_category or place.category or "").strip().lower()
    return (
        place.lat is not None
        and place.lng is not None
        and bool(place.is_active)
        and bool(place.is_published)
        and bool(place.is_visible_in_catalog)
        and bool(place.is_route_eligible)
        and place.publication_status in _ALLOWED_PUBLICATION_STATUSES
        and category not in _BLOCKED_ROUTE_CATEGORIES
    )


def _json_indexes(value: Iterable[int] | None) -> list[int]:
    if value is None:
        return []
    return [int(item) for item in value]


def _next_open_index(total_points: int, closed: set[int]) -> int:
    for index in range(total_points):
        if index not in closed:
            return index
    return total_points
