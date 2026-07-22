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
from services.feature_toggle_service import is_toggle_enabled
from services.routing_projection_candidate_service import (
    ROUTING_PROJECTION_TOGGLE,
    routing_projection_candidates_for_route,
)


def load_ordered_places(db: Session, route: UserRouteState) -> list[Place]:
    if is_toggle_enabled(db, ROUTING_PROJECTION_TOGGLE, default=False):
        by_id = {
            str(place.id): place
            for place in routing_projection_candidates_for_route(db, route)
        }
        return [by_id[point.place_id] for point in route.points if point.place_id in by_id]
    scope = resolve_route_scope(db, route)
    return reconcile_public_route_places(db, route, scope=scope)


def load_place(
    db: Session,
    place_id: str | None,
    *,
    scope: PublicRouteScope | None = None,
) -> Place | None:
    return load_public_route_place(db, place_id, scope=scope)
