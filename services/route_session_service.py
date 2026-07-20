"""Route session lifecycle with hashed ownership tokens."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from models.route import Route
from models.route_session import RouteSession, RouteSessionPoint
from schemas.external_navigation import ExternalNavigationEventRequest
from services.anonymous_ownership import (
    hash_ownership_token,
    issue_ownership_token,
    ownership_tokens_match,
)
from services.external_navigation_service import build_external_navigation, record_external_navigation_event
from services.public_editorial_route_access import (
    load_public_editorial_route_query,
    public_editorial_route_places,
)

_TERMINAL_STATUSES = {"completed", "abandoned"}


class RouteSessionError(ValueError):
    pass


class RouteSessionNotFound(RouteSessionError):
    pass


class RouteSessionConflict(RouteSessionError):
    pass


class RouteSessionUnavailable(RouteSessionError):
    pass


def start_route_session(db: Session, route_id: int, user_key: str | None = None) -> tuple[RouteSession, str]:
    # Canonical public loader (active + published city); keep route_places intact
    # so filtering eligible points does not orphan ORM rows on flush.
    route = load_public_editorial_route_query(db).filter(Route.id == route_id).first()
    if route is None:
        raise RouteSessionNotFound("route_not_found")
    eligible_points = public_editorial_route_places(db, route)
    if len(eligible_points) < 2:
        raise RouteSessionUnavailable("route_has_less_than_two_eligible_points")

    raw_token = issue_ownership_token()
    session = RouteSession(
        route_id=route.id,
        user_key=user_key,
        ownership_token_hash=hash_ownership_token(raw_token),
        status="active",
        current_point_index=0,
    )
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
    return get_route_session(db, session.id, ownership_token=raw_token), raw_token


def get_route_session(db: Session, session_id: int, *, ownership_token: str | None) -> RouteSession:
    session = _load_session(db, session_id)
    _require_ownership(session, ownership_token)
    session.points = sorted(session.points, key=lambda item: item.ordering_index)
    session.navigation = build_external_navigation(session.points)
    return session


def update_route_session(
    db: Session,
    session_id: int,
    *,
    ownership_token: str | None,
    status: str | None = None,
    current_point_index: int | None = None,
) -> RouteSession:
    session = get_route_session(db, session_id, ownership_token=ownership_token)
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
    return get_route_session(db, session_id, ownership_token=ownership_token)


def check_in_route_point(
    db: Session, session_id: int, point_index: int, action: str, *, ownership_token: str | None
) -> RouteSession:
    session = get_route_session(db, session_id, ownership_token=ownership_token)
    if session.status in _TERMINAL_STATUSES:
        raise RouteSessionConflict("route_session_is_terminal")
    if point_index >= len(session.points):
        raise RouteSessionConflict("point_index_out_of_range")
    point = session.points[point_index]
    now = datetime.utcnow()
    visited = set(_json_indexes(session.visited_point_indexes))
    skipped = set(_json_indexes(session.skipped_point_indexes))
    if action == "visit":
        point.is_visited, point.is_skipped = True, False
        point.visited_at, point.skipped_at = now, None
        visited.add(point_index)
        skipped.discard(point_index)
    elif action == "skip":
        point.is_skipped, point.is_visited = True, False
        point.skipped_at, point.visited_at = now, None
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
    return get_route_session(db, session_id, ownership_token=ownership_token)


def complete_route_session(db: Session, session_id: int, *, ownership_token: str | None) -> RouteSession:
    session = get_route_session(db, session_id, ownership_token=ownership_token)
    if session.status == "abandoned":
        raise RouteSessionConflict("route_session_is_abandoned")
    now = datetime.utcnow()
    session.status = "completed"
    session.current_point_index = len(session.points)
    session.completed_at = session.completed_at or now
    session.updated_at = now
    db.commit()
    return get_route_session(db, session_id, ownership_token=ownership_token)


def record_route_session_navigation_event(
    db: Session,
    session_id: int,
    payload: ExternalNavigationEventRequest,
    *,
    ownership_token: str | None,
) -> bool:
    session = get_route_session(db, session_id, ownership_token=ownership_token)
    return record_external_navigation_event(db, route_id=session.route_id, session_id=session.id, payload=payload)


def _load_session(db: Session, session_id: int) -> RouteSession:
    session = (
        db.query(RouteSession)
        .options(joinedload(RouteSession.points))
        .filter(RouteSession.id == session_id)
        .first()
    )
    if session is None:
        raise RouteSessionNotFound("route_session_not_found")
    return session


def _require_ownership(session: RouteSession, ownership_token: str | None) -> None:
    if not ownership_tokens_match(ownership_token, session.ownership_token_hash):
        raise RouteSessionNotFound("route_session_not_found")


def _json_indexes(value: Iterable[int] | None) -> list[int]:
    if value is None:
        return []
    return [int(item) for item in value]


def _next_open_index(total_points: int, closed: set[int]) -> int:
    for index in range(total_points):
        if index not in closed:
            return index
    return total_points
