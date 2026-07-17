from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from models.user_route_state_registry import UserRouteStateRegistry
from schemas.user_route import UserRouteState
from services.public_route_place_access import lock_public_route_state, resolve_route_scope
from services.user_route_state_integrity import sign_user_route_state, verify_user_route_state

ROUTE_STATE_TTL = timedelta(hours=24)
ROUTE_STATE_CLEANUP_BATCH_SIZE = 100


class UserRouteStateConflictError(ValueError):
    pass


def register_initial_route_state(db: Session, state: UserRouteState) -> UserRouteState:
    """Atomically claim a route id and issue state from locked public evidence."""
    cleanup_expired_route_states(db)
    signed = sign_user_route_state(state)
    preliminary_scope = resolve_route_scope(db, signed)
    if preliminary_scope is None:
        raise UserRouteStateConflictError("Route state has no valid public scope.")

    expires_at = _next_expiry()
    values = {
        "route_id": str(signed.route_id),
        "revision": int(signed.revision),
        "city_id": preliminary_scope.city_id,
        "place_ids": _place_ids(signed),
        "token_digest": _token_digest(signed),
        "expires_at": expires_at,
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
    locked_scope = lock_public_route_state(db, signed)
    if (
        registry is None
        or locked_scope is None
        or locked_scope.city_id != preliminary_scope.city_id
        or not _matches(registry, signed, city_id=locked_scope.city_id)
    ):
        raise UserRouteStateConflictError("Route id already belongs to another state or public evidence changed.")
    registry.expires_at = expires_at
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
    if registry is None or _is_expired(registry):
        raise UserRouteStateConflictError("Route state is not registered or has expired.")

    scope = lock_public_route_state(db, state) if lock else resolve_route_scope(db, state)
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
    """Issue one new revision while registry and all public evidence are locked."""
    if str(registry.route_id) != str(previous.route_id) or _is_expired(registry):
        raise UserRouteStateConflictError("Locked registry is invalid or expired.")

    previous_scope = lock_public_route_state(db, previous)
    if previous_scope is None or not _matches(registry, previous, city_id=previous_scope.city_id):
        raise UserRouteStateConflictError("Previous route state lost ownership before advancement.")

    expected_revision = int(previous.revision) + 1
    next_state = next_state.model_copy(update={"route_id": previous.route_id, "revision": expected_revision})
    next_scope = lock_public_route_state(db, next_state)
    if next_scope is None or next_scope.city_id != previous_scope.city_id:
        raise UserRouteStateConflictError("Next route state has no valid matching public scope.")

    signed = sign_user_route_state(next_state)
    registry.revision = expected_revision
    registry.city_id = next_scope.city_id
    registry.place_ids = _place_ids(signed)
    registry.token_digest = _token_digest(signed)
    registry.expires_at = _next_expiry()
    db.flush()
    return signed


def cleanup_expired_route_states(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = ROUTE_STATE_CLEANUP_BATCH_SIZE,
) -> int:
    """Bounded opportunistic cleanup; every new registration removes old state."""
    cutoff = now or datetime.utcnow()
    route_ids = [
        route_id
        for (route_id,) in (
            db.query(UserRouteStateRegistry.route_id)
            .filter(UserRouteStateRegistry.expires_at <= cutoff)
            .order_by(UserRouteStateRegistry.expires_at.asc())
            .limit(max(1, int(limit)))
            .all()
        )
    ]
    if not route_ids:
        return 0
    return int(
        db.query(UserRouteStateRegistry)
        .filter(UserRouteStateRegistry.route_id.in_(route_ids))
        .delete(synchronize_session=False)
    )


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


def _next_expiry() -> datetime:
    return datetime.utcnow() + ROUTE_STATE_TTL


def _is_expired(registry: UserRouteStateRegistry) -> bool:
    return registry.expires_at <= datetime.utcnow()
