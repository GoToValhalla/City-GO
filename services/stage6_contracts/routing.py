from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.route_service import get_public_route_by_id


@dataclass(frozen=True)
class RouteArtifact:
    route_id: int
    city_id: int
    slug: str
    place_ids: tuple[int, ...]


def public_route_artifact(db: Session, route_id: int) -> RouteArtifact | None:
    route = get_public_route_by_id(db, route_id)
    if route is None:
        return None
    return RouteArtifact(
        route_id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        place_ids=tuple(point.place_id for point in route.route_places),
    )
