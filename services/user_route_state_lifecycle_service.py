from __future__ import annotations

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

_SESSION_STARTABLE_STATUSES = frozenset({"ready"})


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

        return self._advance(
            db,
            request.current_route,
            UserRouteCorrectService().correct(db=db, request=request),
        )

    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        return self._advance(
            db,
            request.current_route,
            UserRouteEditService().update_order(db, request),
        )

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        return self._advance(
            db,
            request.current_route,
            UserRouteEditService().replace_place(db, request),
        )

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        return self._advance(
            db,
            request.current_route,
            UserRouteEditService().add_place(db, request),
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
        """Start the separate session aggregate from a full, current route."""
        from services.user_route_session_service import UserRouteSessionService

        state = request.current_route
        verify_current_route_state(db, state, lock=True)
        normalized_status = str(state.status or "").strip().lower()
        if normalized_status not in _SESSION_STARTABLE_STATUSES:
            raise UserRouteStateConflictError(
                f"Route state status {normalized_status or '<empty>'!r} cannot start a session."
            )
        return UserRouteSessionService().start(db, request)

    @staticmethod
    def _advance(db: Session, previous: UserRouteState, next_state: UserRouteState) -> UserRouteState:
        registry = verify_current_route_state(db, previous, lock=True)
        return advance_route_state(
            db,
            previous=previous,
            next_state=sanitize_user_route_state(next_state),
            registry=registry,
        )


__all__ = ["RouteStateLifecycleService", "UserRouteStateConflictError"]
