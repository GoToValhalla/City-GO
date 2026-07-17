from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.route import Route
from models.route_session import RouteSession, RouteSessionPoint
from schemas.user_route import (
    UserRouteSessionActionRequest,
    UserRouteSessionPointState,
    UserRouteSessionStartRequest,
    UserRouteSessionState,
    UserRouteState,
)
from services.public_route_place_access import PublicRouteScope, resolve_route_scope
from services.user_route_place_loader import load_ordered_places

ACTIVE_STATUSES = {"planned", "active", "paused"}
TERMINAL_STATUSES = {"completed", "abandoned"}


class UserRouteSessionError(ValueError):
    pass


class UserRouteSessionService:
    def start(self, db: Session, request: UserRouteSessionStartRequest) -> UserRouteSessionState:
        """Create or return one active session while the caller owns commit/rollback."""
        route_state = request.current_route
        scope = resolve_route_scope(db, route_state)
        places = load_ordered_places(db, route_state)
        if scope is None or not route_state.points:
            raise UserRouteSessionError("Cannot start an invalid or empty route")
        if len(places) != len(route_state.points):
            raise UserRouteSessionError("Route contains places that are no longer available")

        # The locked Route row serializes active-session discovery and creation for
        # one logical user route. A missing Route is claimed through a savepoint so
        # a uniqueness race never rolls back the caller's outer transaction.
        route = self._ensure_locked_route_record(db, route_state, scope)
        existing = (
            db.query(RouteSession)
            .filter(RouteSession.route_id == route.id, RouteSession.status.in_(ACTIVE_STATUSES))
            .order_by(RouteSession.id.desc())
            .first()
        )
        expected_place_ids = [int(place.id) for place in places]
        if existing is not None:
            if _session_place_ids(existing) != expected_place_ids:
                raise UserRouteSessionError("Active route session does not match the current route state")
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
        for index, place in enumerate(places):
            db.add(
                RouteSessionPoint(
                    session_id=session.id,
                    place_id=int(place.id),
                    ordering_index=index,
                    title=place.title,
                    lat=float(place.lat),
                    lng=float(place.lng),
                    is_visited=False,
                    is_skipped=False,
                )
            )
        db.flush()
        return _session_state(session)

    def apply_action(self, db: Session, session_id: int, request: UserRouteSessionActionRequest) -> UserRouteSessionState:
        """Apply one state transition under a row lock; caller owns commit."""
        session = (
            db.query(RouteSession)
            .filter(RouteSession.id == session_id)
            .with_for_update()
            .first()
        )
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
            _require_status(session, ACTIVE_STATUSES)
            session.status = "completed"
            session.completed_at = datetime.utcnow()
        elif request.action == "abandon":
            if session.status not in TERMINAL_STATUSES:
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
        db.flush()
        return _session_state(session)

    def _ensure_locked_route_record(
        self,
        db: Session,
        route_state: UserRouteState,
        scope: PublicRouteScope,
    ) -> Route:
        slug = _route_slug(route_state.route_id)
        route = db.query(Route).filter(Route.slug == slug).with_for_update().first()
        if route is not None:
            return _validate_route_scope(route, scope)

        candidate = Route(
            city_id=scope.city_id,
            slug=slug,
            title=_route_title(route_state),
            short_description=str((route_state.explanation or {}).get("summary") or "User route session"),
            duration_minutes=int(route_state.total_estimated_minutes or route_state.total_minutes or 0),
            distance_km=float(route_state.estimated_distance or 0.0),
            route_mode="walk",
            is_active=True,
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
        except IntegrityError:
            # Only the savepoint is rolled back. No caller-owned pending work is
            # discarded and the outer transaction remains usable.
            route = db.query(Route).filter(Route.slug == slug).with_for_update().first()
            if route is None:
                raise UserRouteSessionError("Concurrent route creation could not be resolved")
            return _validate_route_scope(route, scope)
        return candidate


def _validate_route_scope(route: Route, scope: PublicRouteScope) -> Route:
    if int(route.city_id) != scope.city_id:
        raise UserRouteSessionError("Stored route city does not match the signed route state")
    return route


def _session_place_ids(session: RouteSession) -> list[int]:
    return [int(point.place_id) for point in sorted(list(session.points or []), key=lambda item: int(item.ordering_index))]


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
    point.skipped_at = None
    indexes = set(session.visited_point_indexes or [])
    indexes.add(int(point.ordering_index))
    session.visited_point_indexes = sorted(indexes)
    skipped = set(session.skipped_point_indexes or [])
    skipped.discard(int(point.ordering_index))
    session.skipped_point_indexes = sorted(skipped)


def _skip_point(session: RouteSession, point: RouteSessionPoint) -> None:
    point.is_skipped = True
    point.is_visited = False
    point.skipped_at = datetime.utcnow()
    point.visited_at = None
    indexes = set(session.skipped_point_indexes or [])
    indexes.add(int(point.ordering_index))
    session.skipped_point_indexes = sorted(indexes)
    visited = set(session.visited_point_indexes or [])
    visited.discard(int(point.ordering_index))
    session.visited_point_indexes = sorted(visited)


def _advance_current_index(session: RouteSession) -> None:
    points = sorted(list(session.points or []), key=lambda item: int(item.ordering_index))
    next_open = next((point for point in points if not point.is_visited and not point.is_skipped), None)
    if next_open is None:
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        return
    session.current_point_index = int(next_open.ordering_index)
    if session.status != "paused":
        session.status = "active"


def _route_slug(route_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(route_id))[:180]
    return f"user-route-{safe or 'unknown'}"


def _route_title(route_state: UserRouteState) -> str:
    summary = str((route_state.explanation or {}).get("summary") or "").strip()
    return summary[:255] if summary else f"User route {route_state.route_id}"[:255]


def _public_status(status: str) -> str:
    return status if status in {"active", "paused", "completed", "abandoned"} else "planned"


def _require_status(session: RouteSession, allowed: set[str]) -> None:
    if session.status not in allowed:
        raise UserRouteSessionError(f"Invalid session transition from {session.status}")


def _iso(value: object) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
