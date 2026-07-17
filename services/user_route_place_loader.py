from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import UserRouteState
from services.public_route_place_access import (
    PublicRouteScope,
    load_public_route_place,
    reconcile_public_route_places,
    resolve_route_scope,
)


def load_ordered_places(db: Session, route: UserRouteState) -> list[Place]:
    scope = resolve_route_scope(db, route)
    return reconcile_public_route_places(db, route, scope=scope)


def load_place(
    db: Session,
    place_id: str | None,
    *,
    scope: PublicRouteScope | None = None,
) -> Place | None:
    return load_public_route_place(db, place_id, scope=scope)
