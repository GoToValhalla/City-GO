from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.candidate_retrieval_service import BLOCKED_CITY_LAUNCH_STATUSES, CandidateRetrievalService
from services.place_public_visibility import public_place_conditions, public_route_place_conditions
from services.route_eligibility import route_eligible_sql_conditions


def candidate_diagnostics(db: Session, ctx: object) -> dict[str, object]:
    slug = str(getattr(ctx, "city_id", "") or "")
    city = _city(db, slug)
    city_id = int(city.id) if city else None
    lat, lng = getattr(ctx, "location", (None, None))
    radius = int(getattr(ctx, "radius_meters", 0) or 0)
    return {
        "city_slug": slug or None,
        "city_db_id": city_id,
        "city_launch_status": getattr(city, "launch_status", None),
        "city_is_active": getattr(city, "is_active", None),
        "city_is_blocked_for_routes": _is_blocked_city(city),
        "start_point": {"lat": lat, "lng": lng},
        "location_fallback_applied": bool(getattr(ctx, "location_fallback_applied", False)),
        "location_fallback_reason": getattr(ctx, "location_fallback_reason", None),
        "original_start_point": _location_payload(getattr(ctx, "original_location", None)),
        "city_center_location": _location_payload(getattr(ctx, "city_center_location", None)),
        "distance_to_city_center_meters": getattr(ctx, "distance_to_city_center_meters", None),
        "radius_meters": radius,
        "places_total_in_city": _count(db, city_id, _any_place),
        "places_public_catalog": _count(db, city_id, public_place_conditions()),
        "places_route_visible": _count(db, city_id, public_route_place_conditions()),
        "places_route_eligible": _count(db, city_id, route_eligible_sql_conditions()),
        "places_active_legacy_safe": _count(db, city_id, _active_place),
        "places_with_coords": _count(db, city_id, _with_coords),
        "geo_query_count": _geo_count(db, city_id, lat, lng, radius),
        "geo_route_eligible_count": _geo_route_eligible_count(db, city_id, lat, lng, radius),
        "candidate_retrieval_expected_count": _candidate_expected_count(db, slug, lat, lng, radius),
        "candidate_retrieval_city_wide_expected_count": _candidate_city_wide_expected_count(db, slug),
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


def _geo_route_eligible_count(db: Session, city_id: int | None, lat: object, lng: object, radius: int) -> int:
    if city_id is None or not _is_number(lat) or not _is_number(lng) or radius <= 0:
        return 0
    distance = CandidateRetrievalService()._distance_meters_expr(lat=float(lat), lng=float(lng))
    query = select(func.count(Place.id)).where(
        Place.city_id == city_id,
        distance <= radius,
        *route_eligible_sql_conditions(),
    )
    return _safe_int(db.execute(query).scalar()) or 0


def _candidate_expected_count(db: Session, slug: str, lat: object, lng: object, radius: int) -> int:
    if not slug or not _is_number(lat) or not _is_number(lng) or radius <= 0:
        return 0
    distance = CandidateRetrievalService()._distance_meters_expr(lat=float(lat), lng=float(lng))
    query = (
        select(func.count(Place.id))
        .join(City)
        .where(
            City.slug == slug,
            City.is_active.is_(True),
            ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
            distance <= radius,
            *route_eligible_sql_conditions(),
        )
    )
    return _safe_int(db.execute(query).scalar()) or 0


def _candidate_city_wide_expected_count(db: Session, slug: str) -> int:
    if not slug:
        return 0
    query = (
        select(func.count(Place.id))
        .join(City)
        .where(
            City.slug == slug,
            City.is_active.is_(True),
            ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
            *route_eligible_sql_conditions(),
        )
    )
    return _safe_int(db.execute(query).scalar()) or 0


def _city(db: Session, slug: str) -> City | None:
    if not slug:
        return None
    return db.execute(select(City).where(City.slug == slug)).scalar_one_or_none()


def _is_blocked_city(city: City | None) -> bool:
    if city is None:
        return True
    return bool(not city.is_active or city.launch_status in BLOCKED_CITY_LAUNCH_STATUSES)


def _location_payload(value: object) -> dict[str, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    lat, lng = value
    if not _is_number(lat) or not _is_number(lng):
        return None
    return {"lat": float(lat), "lng": float(lng)}


def _safe_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_any_place = Place.id.is_not(None)
_active_place = Place.is_active.is_(True) & ((Place.status.is_(None)) | (Place.status == "active"))
_with_coords = Place.lat.is_not(None) & Place.lng.is_not(None)
