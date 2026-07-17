from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from schemas.user_route import (
    UserRouteAlternativesResponse,
    UserRouteSessionStartRequest,
    UserRouteSessionState,
    UserRouteState,
)
from services.public_route_sanitizer import sanitize_user_route_state
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)

_SESSION_STARTABLE_STATUSES = frozenset({"ready"})


class RouteStateLifecycleService:
    """Single public owner of the route-state lifecycle.

    Routers and route/session services must use this facade instead of calling
    registry primitives directly. The caller owns commit/rollback; this service
    owns issue/verify/mutate sequencing and the registry -> evidence lock order.

    Read and transition methods are concrete orchestration contracts. They do not
    accept arbitrary callbacks, so a new write cannot be hidden behind a read API.
    """

    def issue_initial(self, db: Session, state: UserRouteState) -> UserRouteState:
        return register_initial_route_state(db, sanitize_user_route_state(state))

    def mutate(
        self,
        db: Session,
        previous: UserRouteState,
        mutation: Callable[[], UserRouteState],
    ) -> UserRouteState:
        registry = verify_current_route_state(db, previous, lock=True)
        next_state = sanitize_user_route_state(mutation())
        return advance_route_state(
            db,
            previous=previous,
            next_state=next_state,
            registry=registry,
        )

    def read_alternatives(
        self,
        db: Session,
        state: UserRouteState,
        place_id: str,
    ) -> UserRouteAlternativesResponse:
        from services.user_route_edit_service import UserRouteEditService

        verify_current_route_state(db, state, lock=True)
        return UserRouteEditService().alternatives(db, state, place_id)

    def start_session(
        self,
        db: Session,
        request: UserRouteSessionStartRequest,
    ) -> UserRouteSessionState:
        """Start the separate session aggregate from a full, current route.

        Preview states are intentionally not promoted implicitly. A client must
        build a full route first, which receives the active-route TTL. Registry
        verification and session creation remain in the caller's one transaction.
        """
        from services.user_route_session_service import UserRouteSessionService

        state = request.current_route
        verify_current_route_state(db, state, lock=True)
        normalized_status = str(state.status or "").strip().lower()
        if normalized_status not in _SESSION_STARTABLE_STATUSES:
            raise UserRouteStateConflictError(
                f"Route state status {normalized_status or '<empty>'!r} cannot start a session."
            )
        return UserRouteSessionService().start(db, request)


__all__ = ["RouteStateLifecycleService", "UserRouteStateConflictError"]
