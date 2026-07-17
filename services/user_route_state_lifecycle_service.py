from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteAlternativesResponse,
    UserRouteCorrectRequest,
    UserRouteReplacePlaceRequest,
    UserRouteSessionStartRequest,
    UserRouteSessionState,
    UserRouteState,
    UserRouteUpdateRequest,
)
from services.public_route_sanitizer import sanitize_user_route_state
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)

_SESSION_STARTABLE_STATUSES = frozenset({"ready", "partial_route", "corrected"})
_READ_ONLY_STATUSES = frozenset({"preview", "preview_failed"})


class RouteStateLifecycleService:
    """Single public owner of the route-state lifecycle.

    Routers and route/session services use concrete facade operations instead of
    registry primitives or executable callbacks. The caller owns commit/rollback;
    this service owns verification, domain operation selection, revision issuance,
    and the registry -> evidence lock order.
    """

    def issue_initial(self, db: Session, state: UserRouteState) -> UserRouteState:
        return register_initial_route_state(db, sanitize_user_route_state(state))

    def correct(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        from services.user_route_correct_service import UserRouteCorrectService

        registry = self._lock_mutable(db, request.current_route)
        next_state = UserRouteCorrectService().correct(db=db, request=request)
        return self._issue_next(db, request.current_route, next_state, registry)

    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        next_state = UserRouteEditService().update_order(db, request)
        return self._issue_next(db, request.current_route, next_state, registry)

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        next_state = UserRouteEditService().replace_place(db, request)
        return self._issue_next(db, request.current_route, next_state, registry)

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        next_state = UserRouteEditService().add_place(db, request)
        return self._issue_next(db, request.current_route, next_state, registry)

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
        """Start the separate session aggregate from a usable, current route."""
        from services.user_route_session_service import UserRouteSessionService

        state = request.current_route
        verify_current_route_state(db, state, lock=True)
        normalized_status = self._normalized_status(state)
        if normalized_status not in _SESSION_STARTABLE_STATUSES:
            raise UserRouteStateConflictError(
                f"Route state status {normalized_status or '<empty>'!r} cannot start a session."
            )
        return UserRouteSessionService().start(db, request)

    @classmethod
    def _lock_mutable(cls, db: Session, state: UserRouteState) -> Any:
        registry = verify_current_route_state(db, state, lock=True)
        normalized_status = cls._normalized_status(state)
        if normalized_status in _READ_ONLY_STATUSES:
            raise UserRouteStateConflictError(
                f"Route state status {normalized_status!r} is read-only and cannot be mutated."
            )
        return registry

    @staticmethod
    def _issue_next(db: Session, previous: UserRouteState, next_state: UserRouteState, registry: Any) -> UserRouteState:
        return advance_route_state(
            db,
            previous=previous,
            next_state=sanitize_user_route_state(next_state),
            registry=registry,
        )

    @staticmethod
    def _normalized_status(state: UserRouteState) -> str:
        return str(state.status or "").strip().lower()


__all__ = ["RouteStateLifecycleService", "UserRouteStateConflictError"]
