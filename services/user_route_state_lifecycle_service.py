from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from schemas.user_route import UserRouteState
from services.public_route_sanitizer import sanitize_user_route_state
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)


class RouteStateLifecycleService:
    """Single public owner of the route-state lifecycle.

    Routers and route/session services must use this facade instead of calling
    registry primitives directly. The caller owns commit/rollback; this service
    owns issue/verify/mutate sequencing and the registry -> evidence lock order.
    """

    def issue_initial(self, db: Session, state: UserRouteState) -> UserRouteState:
        return register_initial_route_state(db, sanitize_user_route_state(state))

    def verify(self, db: Session, state: UserRouteState, *, lock: bool) -> None:
        verify_current_route_state(db, state, lock=lock)

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

    def run_verified_read(
        self,
        db: Session,
        state: UserRouteState,
        operation: Callable[[], object],
    ) -> object:
        verify_current_route_state(db, state, lock=True)
        return operation()


__all__ = ["RouteStateLifecycleService", "UserRouteStateConflictError"]
