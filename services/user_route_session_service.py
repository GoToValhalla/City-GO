from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.route import Route
from models.route_session import RouteSession, RouteSessionPoint
from schemas.user_route import (
    UserRouteSessionActionRequest,
    UserRouteSessionStartRequest,
    UserRouteSessionState,
    UserRouteSessionPointState,
    UserRouteState,
)

ACTIVE_STATUSES = {"planned", "active", "paused"}
TERMINAL_STATUSES = {"completed", "abandoned"}


class UserRouteSessionError(ValueError):
    pass


class UserRouteSessionService:
    def start(self, db: Session, request: UserRouteSessionStartRequest) -> UserRouteSessionState:
        route_state = request.current_route
        if not route_state.points:
            raise UserRouteSessionError("Cannot start an empty route")
        route = self._ensure_route_record(db, route_state)
        existing = (
            db.query(RouteSession)
            .filter(RouteSession.route_id == route.id, RouteSession.status.in_(ACTIVE_STATUSES))
            .order_by(RouteSession.id.desc())
            .first()
        )
        if existing is not None:
            return _session_state(existing)

        session = RouteSession(
            route_id=route.id,
            user_key=request.user_id or route_state.context.user_id,
            status="active",
            current_point_index=0,
            visited_point_indexes=[],
            skipped_point_indexes=[],
            started_at=datetime.utcnow(),
        )
        db.add(session)
        db.flush()
        for index, point in enumerate(route_state.points):
            place_id = _place_id(point.place_id)
            if place_id is None:
                raise UserRouteSessionError(f"Route point {point.place_id} is not a persisted place")
            db.add(
                RouteSessionPoint(
                    session_id=session.id,
                    place_id=place_id,
                    ordering_index=index,
                    title=point.title,
                    lat=point.lat,
                    lng=point.lng,
                    is_visited=False,
                    is_skipped=False,
                )
            )
        db.commit()
        db.refresh(session)
        return _session_state(session)

    def apply_action(self, db: Session, session_id: int, request: UserRouteSessionActionRequest) -> UserRouteSessionState:
        session = db.query(RouteSession).filter(RouteSession.id == session_id).first()
        if session is None:
            raise UserRouteSessionError("Route session not found")
        if session.status in TERMINAL_STATUSES and request.action not in {"abandon"}:
            raise UserRouteSessionError("Route session is already finished")

        if request.action == "pause":
            _require_status(session, {"active"})
            session.status = "paused"
            session.paused_at = datetime.utcnow()
        elif request.action == "resume":
            _require_status(session, {"paused"})
            session.status = "active"
            session.paused_at = None
        elif request.action == "finish":
            session.status = "completed"
            session.completed_at = datetime.utcnow()
        elif request.action == "abandon":
            session.status = "abandoned"
            session.completed_at = datetime.utcnow()
        elif request.action in {"complete_point", "skip_point", "remove_point"}:
            _require_status(session, {"active", "paused"})
            point = _target_point(session, request.place_id)
            if point is None:
                raise UserRouteSessionError("Route session point not found")
            if request.action == "complete_point":
                _complete_point(session, point)
            else:
                _skip_point(session, point)
            _advance_current_index(session)
        else:
            raise UserRouteSessionError(f"Unsupported route session action: {request.action}")

        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        return _session_state(session)

    def _ensure_route_record(self, db: Session, route_state: UserRouteState) -> Route:
        slug = _route_slug(route_state.route_id)
        route = db.query(Route).filter(Route.slug == slug).first()
        if route is not None:
            return route
        city = _city_for_route(db, route_state)
        if city is None:
            raise UserRouteSessionError("Route city not found")
        route = Route(
            city_id=city.id,
            slug=slug,
            title=_route_title(route_state),
            short_description=str((route_state.explanation or {}).get("summary") or "User route session"),
            duration_minutes=int(route_state.total_estimated_minutes or route_state.total_minutes or 0),
            distance_km=float(route_state.estimated_distance or 0.0),
            route_mode="walk",
            is_active=True,
        )
        db.add(route)
        db.flush()
        return route


def _session_state(session: RouteSession) -> UserRouteSessionState:
    points = list(session.points or [])
    current = next((point for point in points if point.ordering_index == session.current_point_index), None)
    next_point = next((point for point in points if point.ordering_index > session.current_point_index and not point.is_visited and not point.is_skipped), None)
    return UserRouteSessionState(
        session_id=int(session.id),
        route_id=str(getattr(session.route, "slug", session.route_id)).removeprefix("user-route-"),
        status=_public_status(session.status),
        current_point_index=int(session.current_point_index or 0),
        current_place_id=str(current.place_id) if current else None,
        next_place_id=str(next_point.place_id) if next_point else None,
        started_at=_iso(session.started_at),
        paused_at=_iso(session.paused_at),
        completed_at=_iso(session.completed_at),
        point_completed_at={str(point.place_id): _iso(point.visited_at) or "" for point in points if point.is_visited},
        skipped_place_ids=[str(point.place_id) for point in points if point.is_skipped],
        points=[
            UserRouteSessionPointState(
                place_id=str(point.place_id),
                title=point.title,
                position=int(point.ordering_index) + 1,
                is_current=int(point.ordering_index) == int(session.current_point_index or 0),
                is_visited=bool(point.is_visited),
                is_skipped=bool(point.is_skipped),
                completed_at=_iso(point.visited_at),
                skipped_at=_iso(point.skipped_at),
            )
            for point in points
        ],
    )


def _target_point(session: RouteSession, place_id: str | None) -> RouteSessionPoint | None:
    points = list(session.points or [])
    if place_id:
        return next((point for point in points if str(point.place_id) == str(place_id)), None)
    return next((point for point in points if int(point.ordering_index) == int(session.current_point_index or 0)), None)


def _complete_point(session: RouteSession, point: RouteSessionPoint) -> None:
    point.is_visited = True
    point.is_skipped = False
    point.visited_at = datetime.utcnow()
    indexes = set(session.visited_point_indexes or [])
    indexes.add(int(point.ordering_index))
    session.visited_point_indexes = sorted(indexes)


def _skip_point(session: RouteSession, point: RouteSessionPoint) -> None:
    point.is_skipped = True
    point.is_visited = False
    point.skipped_at = datetime.utcnow()
    indexes = set(session.skipped_point_indexes or [])
    indexes.add(int(point.ordering_index))
    session.skipped_point_indexes = sorted(indexes)


def _advance_current_index(session: RouteSession) -> None:
    points = sorted(list(session.points or []), key=lambda item: int(item.ordering_index))
    next_open = next((point for point in points if not point.is_visited and not point.is_skipped), None)
    if next_open is None:
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        return
    session.current_point_index = int(next_open.ordering_index)
    if session.status == "paused":
        return
    session.status = "active"


def _city_for_route(db: Session, route_state: UserRouteState) -> City | None:
    city_slug = route_state.context.city_id or route_state.context.visit_city_id or (route_state.points[0].city_slug if route_state.points else None)
    if city_slug:
        city = db.query(City).filter(City.slug == str(city_slug)).first()
        if city is not None:
            return city
    first_place_id = _place_id(route_state.points[0].place_id) if route_state.points else None
    if first_place_id:
        place = db.query(Place).filter(Place.id == first_place_id).first()
        if place is not None:
            return db.query(City).filter(City.id == place.city_id).first()
    return None


def _route_slug(route_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(route_id))[:180]
    return f"user-route-{safe or 'unknown'}"


def _route_title(route_state: UserRouteState) -> str:
    summary = str((route_state.explanation or {}).get("summary") or "").strip()
    return summary[:255] if summary else f"User route {route_state.route_id}"[:255]


def _public_status(status: str) -> str:
    if status in {"active", "paused", "completed", "abandoned"}:
        return status
    return "planned"


def _require_status(session: RouteSession, allowed: set[str]) -> None:
    if session.status not in allowed:
        raise UserRouteSessionError(f"Invalid session transition from {session.status}")


def _place_id(value: str | int | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _iso(value: object) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
