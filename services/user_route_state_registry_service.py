from __future__ import annotations

import hashlib

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteState
from services.public_route_place_access import resolve_route_scope
from services.user_route_state_integrity import sign_user_route_state, verify_user_route_state


class UserRouteStateConflictError(ValueError):
    pass


def register_initial_route_state(db: Session, state: UserRouteState) -> UserRouteState:
    """Atomically claim a route id and register its first server-issued state.

    The caller owns commit/rollback. Missing-row races are resolved by an
    INSERT .. ON CONFLICT DO NOTHING primitive, never by SELECT FOR UPDATE on a
    row that does not yet exist.
    """
    signed = sign_user_route_state(state)
    scope = resolve_route_scope(db, signed)
    if scope is None:
        raise UserRouteStateConflictError("Route state has no valid public scope.")

    values = {
        "route_id": str(signed.route_id),
        "revision": int(signed.revision),
        "city_id": scope.city_id,
        "place_ids": _place_ids(signed),
        "token_digest": _token_digest(signed),
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = pg_insert(UserRouteStateRegistry).values(**values).on_conflict_do_nothing(
            index_elements=[UserRouteStateRegistry.route_id]
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(UserRouteStateRegistry).values(**values).on_conflict_do_nothing(
            index_elements=[UserRouteStateRegistry.route_id]
        )
    else:
        raise UserRouteStateConflictError(f"Unsupported registry database dialect: {dialect}")

    db.execute(statement)
    registry = _locked_registry(db, str(signed.route_id))
    if registry is None or not _matches(registry, signed, city_id=scope.city_id):
        raise UserRouteStateConflictError("Route id already belongs to another state.")
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
    registry: UserRouteStateRegistry,
) -> UserRouteState:
    """Issue exactly one new revision while the caller holds registry's row lock.

    Every accepted mutation, including a semantic no-op carrying a warning,
    advances the revision. This makes the previous signed state unusable for
    replay and removes a second, divergent no-op lifecycle.
    """
    if str(registry.route_id) != str(previous.route_id):
        raise UserRouteStateConflictError("Locked registry does not belong to the previous route state.")
    scope = resolve_route_scope(db, previous)
    if scope is None or not _matches(registry, previous, city_id=scope.city_id):
        raise UserRouteStateConflictError("Previous route state lost ownership before advancement.")

    expected_revision = int(previous.revision) + 1
    next_state = next_state.model_copy(update={"route_id": previous.route_id, "revision": expected_revision})
    signed = sign_user_route_state(next_state)
    next_scope = resolve_route_scope(db, signed)
    if next_scope is None or next_scope.city_id != scope.city_id:
        raise UserRouteStateConflictError("Next route state has no valid matching public scope.")

    registry.revision = expected_revision
    registry.city_id = next_scope.city_id
    registry.place_ids = _place_ids(signed)
    registry.token_digest = _token_digest(signed)
    db.flush()
    return signed


def _locked_registry(db: Session, route_id: str) -> UserRouteStateRegistry | None:
    return (
        db.query(UserRouteStateRegistry)
        .filter(UserRouteStateRegistry.route_id == route_id)
        .with_for_update()
        .first()
    )


def _matches(registry: UserRouteStateRegistry, state: UserRouteState, *, city_id: int) -> bool:
    return (
        int(registry.revision) == int(state.revision)
        and int(registry.city_id) == int(city_id)
        and list(registry.place_ids or []) == _place_ids(state)
        and str(registry.token_digest) == _token_digest(state)
    )


def _place_ids(state: UserRouteState) -> list[int]:
    try:
        return [int(point.place_id) for point in state.points]
    except (TypeError, ValueError) as exc:
        raise UserRouteStateConflictError("Route state contains a non-persisted place id.") from exc


def _token_digest(state: UserRouteState) -> str:
    token = str(state.state_token or "")
    if not token:
        raise UserRouteStateConflictError("Route state token is missing.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
