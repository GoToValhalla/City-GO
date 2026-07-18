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
from services.user_route_mutation_result import RouteMutationResult
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)

_SESSION_STARTABLE_STATUSES = frozenset({"ready", "partial_route"})
_READ_ONLY_STATUSES = frozenset({"preview", "preview_failed"})
_LIFECYCLE_METADATA_FIELDS = frozenset(
    {
        "revision",
        "state_token",
        "signature",
        "signatures",
        "timestamp",
        "timestamps",
    }
)


class UserRouteMutationRejectedError(ValueError):
    pass


class RouteStateLifecycleService:
    """Single public owner of the route-state lifecycle.

    Domain services return an explicit RouteMutationResult. Only accepted outcomes
    that change the authoritative domain payload may advance revision, token digest,
    or expiry. Rejected and no-op outcomes leave the registry unchanged.
    """

    def issue_initial(self, db: Session, state: UserRouteState) -> UserRouteState:
        return register_initial_route_state(db, sanitize_user_route_state(state))

    def correct(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        from services.user_route_correct_service import UserRouteCorrectService

        registry = self._lock_mutable(db, request.current_route)
        result = UserRouteCorrectService().correct(db=db, request=request)
        return self._issue_accepted(db, request.current_route, result, registry)

    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        result = UserRouteEditService().update_order(db, request)
        return self._issue_accepted(db, request.current_route, result, registry)

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        result = UserRouteEditService().replace_place(db, request)
        return self._issue_accepted(db, request.current_route, result, registry)

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> UserRouteState:
        from services.user_route_edit_service import UserRouteEditService

        registry = self._lock_mutable(db, request.current_route)
        result = UserRouteEditService().add_place(db, request)
        return self._issue_accepted(db, request.current_route, result, registry)

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
    def _issue_accepted(
        db: Session,
        previous: UserRouteState,
        result: RouteMutationResult,
        registry: Any,
    ) -> UserRouteState:
        if not result.accepted or result.state is None:
            raise UserRouteMutationRejectedError(
                str(result.reason or "Route mutation was rejected.")
            )

        previous_state = sanitize_user_route_state(previous)
        next_state = sanitize_user_route_state(result.state)
        if _canonical_domain_payload(previous_state) == _canonical_domain_payload(next_state):
            raise UserRouteMutationRejectedError(
                "Route mutation did not change authoritative state."
            )

        return advance_route_state(
            db,
            previous=previous,
            next_state=next_state,
            registry=registry,
        )

    @staticmethod
    def _normalized_status(state: UserRouteState) -> str:
        return str(state.status or "").strip().lower()


def _canonical_domain_payload(state: UserRouteState) -> Any:
    return _strip_lifecycle_metadata(state.model_dump(mode="json"))


def _strip_lifecycle_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_lifecycle_metadata(item)
            for key, item in value.items()
            if str(key).strip().lower() not in _LIFECYCLE_METADATA_FIELDS
        }
    if isinstance(value, list):
        return [_strip_lifecycle_metadata(item) for item in value]
    return value


__all__ = [
    "RouteStateLifecycleService",
    "UserRouteMutationRejectedError",
    "UserRouteStateConflictError",
]
