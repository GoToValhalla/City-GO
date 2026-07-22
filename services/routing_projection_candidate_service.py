"""Shared projection-only route candidate source."""

from math import atan2, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.search_routing_stage5 import RouteCandidateSet, RoutingPlaceNode
from services.projection_readiness_service import assert_projection_ready
from services.public_read_projection_service import PublicReadProjectionError, REASON_EMPTY, REASON_INCOMPLETE, REASON_STALE, REASON_VERSION
from services.projection_observability import log_projection_read
from time import perf_counter
from types import SimpleNamespace

ROUTING_PROJECTION_TOGGLE = "routing_projection_reads_enabled"


def routing_projection_candidates_for_route(db: Session, route: object) -> list[Place]:
    context = getattr(route, "context", route)
    return routing_projection_candidates(
        db,
        SimpleNamespace(
            city_id=getattr(context, "city_id", None),
            destination_id=getattr(context, "destination_id", None),
            location=None,
            radius_meters=0,
            avoided_place_ids=[],
            avoided_categories=[],
        ),
    )


def routing_projection_candidates(db: Session, ctx: object) -> list[Place]:
    started = perf_counter()
    city = db.query(City).filter(City.slug == str(getattr(ctx, "city_id", "")), City.is_active.is_(True), City.launch_status == "published").first()
    if city is None:
        return []
    node_status = assert_projection_ready(db, projection_type="routing_place_node", city_id=int(city.id))
    set_status = assert_projection_ready(db, projection_type="route_candidate_set", city_id=int(city.id))
    if node_status.source_version != set_status.source_version:
        raise PublicReadProjectionError("Routing projection versions differ", reason=REASON_VERSION)
    candidate_set = db.query(RouteCandidateSet).filter(
        RouteCandidateSet.city_id == city.id, RouteCandidateSet.profile == "overview",
        RouteCandidateSet.route_policy == "city_walking", RouteCandidateSet.freshness_status == "fresh",
    ).order_by(RouteCandidateSet.source_snapshot_version.desc()).first()
    if candidate_set is None:
        raise PublicReadProjectionError("Route candidate set is missing", reason=REASON_EMPTY)
    place_ids = [int(value) for value in (candidate_set.payload or {}).get("place_ids", [])]
    if candidate_set.candidate_count != len(place_ids):
        raise PublicReadProjectionError("Route candidate set is incomplete", reason=REASON_INCOMPLETE)
    if not place_ids and node_status.expected_count > 0:
        raise PublicReadProjectionError("Route candidate set is empty", reason=REASON_EMPTY)
    nodes = db.query(RoutingPlaceNode).filter(
        RoutingPlaceNode.place_id.in_(place_ids), RoutingPlaceNode.city_id == city.id,
        RoutingPlaceNode.is_route_visible.is_(True), RoutingPlaceNode.freshness_status == "fresh",
    ).all()
    by_id = {int(row.place_id): row for row in nodes}
    if set(by_id) != set(place_ids):
        raise PublicReadProjectionError("Routing nodes are incomplete", reason=REASON_INCOMPLETE)
    ordered = [by_id[value] for value in place_ids]
    filtered = [row for row in ordered if _matches(row, ctx)]
    result = [_place(row) for row in sorted(filtered, key=lambda row: (-row.quality_score, row.place_id))]
    log_projection_read(read_path="routing", projection_type="routing_place_node", city_id=int(city.id),
                        uses_projection=True, latency_ms=int((perf_counter() - started) * 1000),
                        source_version=node_status.source_version, projection_version=node_status.projection_version)
    return result


def _matches(node: RoutingPlaceNode, ctx: object) -> bool:
    payload = node.place_payload or {}
    avoided_ids = {int(value) for value in getattr(ctx, "avoided_place_ids", []) or []}
    avoided_categories = {str(value).lower() for value in getattr(ctx, "avoided_categories", []) or []}
    if node.place_id in avoided_ids or str(node.category or "").lower() in avoided_categories:
        return False
    destination_id = getattr(ctx, "destination_id", None)
    if destination_id is not None and int(destination_id) not in payload.get("destination_ids", []):
        return False
    location = getattr(ctx, "location", None)
    radius = int(getattr(ctx, "radius_meters", 0) or 0)
    return not location or not radius or _distance(float(location[0]), float(location[1]), node.lat, node.lng) <= radius


def _place(node: RoutingPlaceNode) -> Place:
    payload = dict(node.place_payload or {})
    payload.pop("destination_ids", None)
    payload.update({"id": node.place_id, "city_id": node.city_id, "lat": node.lat, "lng": node.lng, "category": node.category, "is_published": True, "is_route_eligible": True, "is_active": True, "status": payload.get("status", "active"), "publication_status": payload.get("publication_status", "published")})
    return Place(**payload)


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    value = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 6_371_000 * 2 * atan2(sqrt(value), sqrt(1 - value))
