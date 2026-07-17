from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteState
from services.public_route_place_access import resolve_route_scope
from services.user_route_state_integrity import sign_user_route_state, verify_user_route_state


class UserRouteStateConflictError(ValueError):
    pass


def register_initial_route_state(db: Session, state: UserRouteState) -> UserRouteState:
    signed = sign_user_route_state(state)
    scope = resolve_route_scope(db, signed)
    if scope is None:
        raise UserRouteStateConflictError("Route state has no valid public scope.")

    existing = (
        db.query(UserRouteStateRegistry)
        .filter(UserRouteStateRegistry.route_id == signed.route_id)
        .with_for_update()
        .first()
    )
    if existing is not None:
        if _matches(existing, signed, city_id=scope.city_id):
            return signed
        raise UserRouteStateConflictError("Route id already belongs to another state.")

    db.add(
        UserRouteStateRegistry(
            route_id=str(signed.route_id),
            revision=int(signed.revision),
            city_id=scope.city_id,
            place_ids=_place_ids(signed),
            token_digest=_token_digest(signed),
        )
    )
    db.flush()
    return signed


def verify_current_route_state(
    db: Session,
    state: UserRouteState,
    *,
    lock: bool,
) -> UserRouteStateRegistry:
    verify_user_route_state(state)
    query = db.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.route_id == state.route_id)
    if lock:
        query = query.with_for_update()
    registry = query.first()
    if registry is None:
        raise UserRouteStateConflictError("Route state is not registered.")

    scope = resolve_route_scope(db, state)
    if scope is None or not _matches(registry, state, city_id=scope.city_id):
        raise UserRouteStateConflictError("Route state is stale or does not match the current server revision.")
    return registry


def advance_route_state(
    db: Session,
    *,
    previous: UserRouteState,
    next_state: UserRouteState,
) -> UserRouteState:
    registry = verify_current_route_state(db, previous, lock=True)
    expected_revision = int(previous.revision) + 1
    if int(next_state.revision) != expected_revision:
        raise UserRouteStateConflictError("Route revision must advance exactly once.")

    next_state = next_state.model_copy(update={"route_id": previous.route_id, "revision": expected_revision})
    signed = sign_user_route_state(next_state)
    scope = resolve_route_scope(db, signed)
    if scope is None:
        raise UserRouteStateConflictError("Next route state has no valid public scope.")

    registry.revision = expected_revision
    registry.city_id = scope.city_id
    registry.place_ids = _place_ids(signed)
    registry.token_digest = _token_digest(signed)
    db.flush()
    return signed


def _matches(registry: UserRouteStateRegistry, state: UserRouteState, *, city_id: int) -> bool:
    return (
        int(registry.revision) == int(state.revision)
        and int(registry.city_id) == int(city_id)
        and list(registry.place_ids or []) == _place_ids(state)
        and str(registry.token_digest) == _token_digest(state)
    )


def _place_ids(state: UserRouteState) -> list[int]:
    return [int(point.place_id) for point in state.points]


def _token_digest(state: UserRouteState) -> str:
    token = str(state.state_token or "")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
