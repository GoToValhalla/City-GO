from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.candidate_retrieval_service import CandidateRetrievalService
from services.place_public_visibility import public_place_conditions, public_route_place_conditions
from services.route_eligibility import route_eligible_sql_conditions


def candidate_diagnostics(db: Session, ctx: object) -> dict[str, object]:
    slug = str(getattr(ctx, "city_id", "") or "")
    city_id = _city_id(db, slug)
    lat, lng = getattr(ctx, "location", (None, None))
    radius = int(getattr(ctx, "radius_meters", 0) or 0)
    return {
        "city_slug": slug or None,
        "city_db_id": city_id,
        "start_point": {"lat": lat, "lng": lng},
        "radius_meters": radius,
        "places_total_in_city": _count(db, city_id, _any_place),
        "places_public_catalog": _count(db, city_id, public_place_conditions()),
        "places_route_visible": _count(db, city_id, public_route_place_conditions()),
        "places_route_eligible": _count(db, city_id, route_eligible_sql_conditions()),
        "places_active_legacy_safe": _count(db, city_id, _active_place),
        "places_with_coords": _count(db, city_id, _with_coords),
        "geo_query_count": _geo_count(db, city_id, lat, lng, radius),
    }


def _count(db: Session, city_id: int | None, predicates: object | tuple[object, ...]) -> int:
    if city_id is None:
        return 0
    predicate_tuple = predicates if isinstance(predicates, tuple) else (predicates,)
    query = select(func.count(Place.id)).where(Place.city_id == city_id, *predicate_tuple)
    return _safe_int(db.execute(query).scalar()) or 0


def _geo_count(db: Session, city_id: int | None, lat: object, lng: object, radius: int) -> int:
    if city_id is None or not _is_number(lat) or not _is_number(lng) or radius <= 0:
        return 0
    distance = CandidateRetrievalService()._distance_meters_expr(lat=float(lat), lng=float(lng))
    query = select(func.count(Place.id)).where(
        Place.city_id == city_id,
        distance <= radius,
        *public_route_place_conditions(),
    )
    return _safe_int(db.execute(query).scalar()) or 0


def _city_id(db: Session, slug: str) -> int | None:
    if not slug:
        return None
    return _safe_int(db.execute(select(City.id).where(City.slug == slug)).scalar_one_or_none())


def _safe_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_any_place = Place.id.is_not(None)
_active_place = or_(Place.is_active.is_(True), Place.is_active.is_(None)) & or_(Place.status.is_(None), Place.status == "active")
_with_coords = Place.lat.is_not(None) & Place.lng.is_not(None)
