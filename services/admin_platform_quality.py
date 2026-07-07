from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_photo_candidate import PlacePhotoCandidate
from services.data_quality.constants import STOPLIST_CATEGORIES

NON_TOURIST_LAYERS = {"service_layer", "transport_layer", "admin_evidence_only"}
PHOTO_CANDIDATE_OPEN_STATUSES = {"candidate", "pending", "needs_review", "open"}
LANDMARK_CATEGORIES = {"landmark", "monument", "memorial", "viewpoint", "square", "attraction", "church", "cathedral"}
MUSEUM_CATEGORIES = {"museum", "gallery", "paid_attraction", "theatre", "theater", "cinema"}
PARK_CATEGORIES = {"park", "promenade", "beach", "garden"}
RESTAURANT_CATEGORIES = {"restaurant", "cafe", "bar", "food"}
KNOWN_TOURIST_CATEGORIES = LANDMARK_CATEGORIES | MUSEUM_CATEGORIES | PARK_CATEGORIES | RESTAURANT_CATEGORIES
HOURS_APPLICABLE_CATEGORIES = MUSEUM_CATEGORIES | PARK_CATEGORIES | RESTAURANT_CATEGORIES
HOURS_REQUIRED_CATEGORIES = MUSEUM_CATEGORIES
ADDRESS_REQUIRED_CATEGORIES = MUSEUM_CATEGORIES | RESTAURANT_CATEGORIES


def city_quality_row(db: Session, city: City, category: str | None = None) -> dict[str, Any]:
    places_query = db.query(Place).filter(Place.city_id == city.id)
    if category:
        places_query = places_query.filter(Place.category == category)
    row = _aggregate_query(places_query).one()
    pending = _pending_photo_review_by_city(db, [city.id], category).get(city.id, 0)
    return _build_city_quality_row_from_agg(city, row, pending_photo_review_total=pending)


def quality_summary(
    db: Session,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, object]:
    cities_query = db.query(City)
    if city_slug:
        cities_query = cities_query.filter(City.slug == city_slug)
    if region:
        cities_query = cities_query.filter(City.region == region)

    total_cities = int(cities_query.count() or 0)
    safe_limit = max(1, min(50, int(limit or 25)))
    safe_offset = max(0, int(offset or 0))
    cities = cities_query.order_by(City.name.asc()).offset(safe_offset).limit(safe_limit).all()
    if not cities:
        return {"items": [], "total": total_cities, "todo": [], "limit": safe_limit, "offset": safe_offset}

    city_ids = [city.id for city in cities]
    places_query = db.query(Place).filter(Place.city_id.in_(city_ids))
    if category:
        places_query = places_query.filter(Place.category == category)
    agg_rows = _aggregate_query(places_query, include_city_id=True).group_by(Place.city_id).all()
    agg_map = {row.city_id: row for row in agg_rows}
    pending_photo_map = _pending_photo_review_by_city(db, city_ids, category)

    rows: list[dict[str, Any]] = []
    for city in cities:
        agg_row = agg_map.get(city.id)
        quality = _empty_city_quality_row(city) if agg_row is None else _build_city_quality_row_from_agg(
            city,
            agg_row,
            pending_photo_review_total=pending_photo_map.get(city.id, 0),
        )
        coverage = quality["critical_coverage"] if isinstance(quality.get("critical_coverage"), dict) else {}
        rows.append({
            "city_slug": city.slug,
            "city_name": city.name,
            "region": city.region,
            "readiness_score": quality["readiness_score"],
            "stored_readiness_score": quality["stored_readiness_score"],
            "places_total": quality["places_total"],
            "review_universe_total": quality["review_universe_total"],
            "manual_review_total": quality["manual_review_total"],
            "auto_excluded_total": quality["auto_excluded_total"],
            "severity": _severity(int(quality["readiness_score"]), quality["manual_review_total"]),
            "blockers": quality["blockers"],
            "primary_blocker": quality["primary_blocker"],
            "route_candidate_total": int(coverage.get("route_candidate_total", 0) or 0),
            "route_ready_total": int(coverage.get("route_ready_total", 0) or 0),
            "route_blockers_total": int(coverage.get("route_blockers_total", 0) or 0),
            "card_ready_total": int(coverage.get("card_ready_total", 0) or 0),
            "card_blockers_total": int(coverage.get("card_blockers_total", 0) or 0),
            "auto_enrichment_total": int(coverage.get("auto_enrichment_total", 0) or 0),
            "critical_manual_review_total": int(coverage.get("manual_review_total", 0) or 0),
            "optional_gaps_total": int(coverage.get("optional_gaps_total", 0) or 0),
            "not_applicable_total": int(coverage.get("not_applicable_total", 0) or 0),
            "critical_coverage": coverage,
        })
    if severity:
        rows = [row for row in rows if row["severity"] == severity]
    return {"items": rows, "total": total_cities if not severity else len(rows), "todo": _todo(rows), "limit": safe_limit, "offset": safe_offset}


def _aggregate_query(places_query, *, include_city_id: bool = False):
    conditions = _critical_conditions()
    columns = [
        func.count(Place.id).label("places_total"),
        func.sum(case((conditions["tourist"], 1), else_=0)).label("review_universe_total"),
        func.sum(case((conditions["missing_photo"], 1), else_=0)).label("no_photo"),
        func.sum(case((conditions["missing_address_any"], 1), else_=0)).label("no_address"),
        func.sum(case((conditions["manual_review"], 1), else_=0)).label("manual_review_total"),
        func.sum(case((conditions["missing_description"], 1), else_=0)).label("no_description"),
        func.sum(case((conditions["missing_opening_hours_required"], 1), else_=0)).label("missing_opening_hours"),
        func.sum(case((conditions["missing_opening_hours_applicable"], 1), else_=0)).label("missing_opening_hours_applicable"),
        func.sum(case((conditions["route_blocker"], 1), else_=0)).label("route_blockers_total"),
        func.sum(case((conditions["card_blocker"], 1), else_=0)).label("card_blockers_total"),
        func.sum(case((conditions["route_ineligible"], 1), else_=0)).label("route_ineligible_total"),
        func.sum(case((conditions["missing_category"], 1), else_=0)).label("missing_category_total"),
        func.sum(case((conditions["unknown_category"], 1), else_=0)).label("unknown_category_total"),
        func.sum(case((conditions["hours_applicable"], 1), else_=0)).label("hours_applicable_total"),
        func.sum(case((conditions["has_opening_hours_applicable"], 1), else_=0)).label("has_opening_hours_total"),
        func.sum(case((conditions["missing_address_required"], 1), else_=0)).label("missing_required_address"),
    ]
    if include_city_id:
        columns.insert(0, Place.city_id)
    return places_query.with_entities(*columns)


def _critical_conditions() -> dict[str, Any]:
    category = func.lower(func.coalesce(Place.canonical_category, Place.category, ""))
    tourist = ~category.in_(tuple(STOPLIST_CATEGORIES)) & ~Place.place_layer.in_(tuple(NON_TOURIST_LAYERS)) & Place.tourist_eligible.is_not(False)
    known_tourist = category.in_(tuple(KNOWN_TOURIST_CATEGORIES))
    hours_required = category.in_(tuple(HOURS_REQUIRED_CATEGORIES))
    hours_applicable = tourist & category.in_(tuple(HOURS_APPLICABLE_CATEGORIES))
    address_required = category.in_(tuple(ADDRESS_REQUIRED_CATEGORIES))
    missing_photo = tourist & _missing_text(Place.image_url)
    missing_address_any = tourist & _missing_text(Place.address)
    missing_description = tourist & _missing_text(Place.short_description)
    missing_address_required = tourist & address_required & _missing_text(Place.address)
    missing_opening_hours_required = tourist & hours_required & Place.opening_hours.is_(None)
    route_ineligible = tourist & Place.is_route_eligible.is_(False)
    missing_category = tourist & (category == "")
    unknown_category = tourist & (category != "") & ~known_tourist
    route_blocker = route_ineligible | missing_category | unknown_category | missing_opening_hours_required
    return {
        "tourist": tourist,
        "missing_photo": missing_photo,
        "missing_address_any": missing_address_any,
        "manual_review": missing_photo | missing_address_any,
        "missing_description": missing_description,
        "missing_address_required": missing_address_required,
        "missing_opening_hours_required": missing_opening_hours_required,
        "missing_opening_hours_applicable": hours_applicable & Place.opening_hours.is_(None),
        "route_blocker": route_blocker,
        "card_blocker": missing_photo | missing_address_required,
        "route_ineligible": route_ineligible,
        "missing_category": missing_category,
        "unknown_category": unknown_category,
        "hours_applicable": hours_applicable,
        "has_opening_hours_applicable": hours_applicable & Place.opening_hours.is_not(None),
    }


def _pending_photo_review_by_city(db: Session, city_ids: list[int], category: str | None = None) -> dict[int, int]:
    if not city_ids:
        return {}
    query = (
        db.query(Place.city_id, func.count(func.distinct(Place.id)).label("pending_photo_review"))
        .join(PlacePhotoCandidate, PlacePhotoCandidate.place_id == Place.id)
        .filter(
            Place.city_id.in_(city_ids),
            PlacePhotoCandidate.status.in_(tuple(PHOTO_CANDIDATE_OPEN_STATUSES)),
            ~func.lower(func.coalesce(Place.canonical_category, Place.category, "")).in_(tuple(STOPLIST_CATEGORIES)),
            _missing_text(Place.image_url),
        )
    )
    if category:
        query = query.filter(Place.category == category)
    return {city_id: int(count or 0) for city_id, count in query.group_by(Place.city_id).all()}


def _missing_text(column):
    return or_(column.is_(None), column == "")


def _int_attr(row: Any, name: str) -> int:
    return int(getattr(row, name, 0) or 0)


def _pct(count: int, total: int) -> float:
    return round((count / total) * 100, 1) if total else 100.0


def _build_city_quality_row_from_agg(city: City, agg_row: Any, *, pending_photo_review_total: int = 0) -> dict[str, Any]:
    places_total = _int_attr(agg_row, "places_total")
    review_universe_total = _int_attr(agg_row, "review_universe_total")
    no_photo_total = _int_attr(agg_row, "no_photo")
    no_address_total = _int_attr(agg_row, "no_address")
    no_description_total = _int_attr(agg_row, "no_description")
    missing_required_address_total = _int_attr(agg_row, "missing_required_address")
    missing_opening_hours_total = _int_attr(agg_row, "missing_opening_hours")
    missing_opening_hours_applicable_total = _int_attr(agg_row, "missing_opening_hours_applicable")
    route_blockers_total = _int_attr(agg_row, "route_blockers_total")
    card_blockers_total = _int_attr(agg_row, "card_blockers_total")
    route_ineligible_total = _int_attr(agg_row, "route_ineligible_total")
    missing_category_total = _int_attr(agg_row, "missing_category_total")
    unknown_category_total = _int_attr(agg_row, "unknown_category_total")
    hours_applicable_total = _int_attr(agg_row, "hours_applicable_total")
    has_opening_hours_total = _int_attr(agg_row, "has_opening_hours_total")
    manual_review_total = max(_int_attr(agg_row, "manual_review_total"), int(pending_photo_review_total or 0))
    excluded_total = max(0, places_total - review_universe_total)
    route_ready_total = max(0, review_universe_total - route_blockers_total)
    card_ready_total = max(0, review_universe_total - card_blockers_total)
    blockers = {key: value for key, value in {"no_photo": no_photo_total, "no_address": no_address_total, "missing_opening_hours": missing_opening_hours_total}.items() if value}
    readiness = _readiness_score(review_universe_total, no_photo_total, no_address_total)
    coverage = _fast_critical_coverage(
        places_total=places_total,
        review_universe_total=review_universe_total,
        route_ready_total=route_ready_total,
        route_blockers_total=route_blockers_total,
        card_ready_total=card_ready_total,
        card_blockers_total=card_blockers_total,
        manual_review_total=manual_review_total,
        excluded_total=excluded_total,
        no_photo_total=no_photo_total,
        no_address_total=no_address_total,
        no_description_total=no_description_total,
        missing_required_address_total=missing_required_address_total,
        missing_opening_hours_total=missing_opening_hours_total,
        missing_opening_hours_applicable_total=missing_opening_hours_applicable_total,
        route_ineligible_total=route_ineligible_total,
        missing_category_total=missing_category_total,
        unknown_category_total=unknown_category_total,
        hours_applicable_total=hours_applicable_total,
        has_opening_hours_total=has_opening_hours_total,
        pending_photo_review_total=int(pending_photo_review_total or 0),
    )
    return {
        "readiness_score": readiness,
        "stored_readiness_score": int(getattr(city, "readiness_score", 0) or 0),
        "primary_blocker": _primary_blocker(blockers, readiness),
        "blockers": {**blockers, "excluded_by_design": excluded_total},
        "places_total": places_total,
        "review_universe_total": review_universe_total,
        "manual_review_total": manual_review_total,
        "auto_excluded_total": excluded_total,
        "critical_coverage": coverage,
    }


def _empty_city_quality_row(city: City) -> dict[str, Any]:
    empty = _fast_critical_coverage(
        places_total=0,
        review_universe_total=0,
        route_ready_total=0,
        route_blockers_total=0,
        card_ready_total=0,
        card_blockers_total=0,
        manual_review_total=0,
        excluded_total=0,
        no_photo_total=0,
        no_address_total=0,
        no_description_total=0,
        missing_required_address_total=0,
        missing_opening_hours_total=0,
        missing_opening_hours_applicable_total=0,
        route_ineligible_total=0,
        missing_category_total=0,
        unknown_category_total=0,
        hours_applicable_total=0,
        has_opening_hours_total=0,
        pending_photo_review_total=0,
    )
    return {
        "readiness_score": 0,
        "stored_readiness_score": int(getattr(city, "readiness_score", 0) or 0),
        "primary_blocker": None,
        "blockers": {"excluded_by_design": 0},
        "places_total": 0,
        "review_universe_total": 0,
        "manual_review_total": 0,
        "auto_excluded_total": 0,
        "critical_coverage": empty,
    }


def _readiness_score(review_universe_total: int, no_photo_total: int, no_address_total: int) -> int:
    if review_universe_total <= 0:
        return 0
    penalty = 30 * (no_photo_total / review_universe_total) + 30 * (no_address_total / review_universe_total)
    return max(0, min(100, round(100 - penalty)))


def _primary_blocker(blockers: dict[str, int], readiness: int) -> str | None:
    if readiness >= 100:
        return None
    if blockers.get("no_photo"):
        return "no_photo"
    if blockers.get("no_address"):
        return "no_address"
    if blockers.get("missing_opening_hours"):
        return "missing_opening_hours"
    return None


def _fast_critical_coverage(**values: int) -> dict[str, Any]:
    review_total = values["review_universe_total"]
    no_photo = values["no_photo_total"]
    no_address = values["no_address_total"]
    no_description = values["no_description_total"]
    has_hours = values["has_opening_hours_total"]
    hours_total = values["hours_applicable_total"]
    route_ready = values["route_ready_total"]
    route_blockers = values["route_blockers_total"]
    card_ready = values["card_ready_total"]
    card_blockers = values["card_blockers_total"]
    manual_review = values["manual_review_total"]
    excluded = values["excluded_total"]
    coverage = {
        "has_approved_photo": {"count": max(0, review_total - no_photo), "total": review_total, "pct": _pct(max(0, review_total - no_photo), review_total)},
        "has_address": {"count": max(0, review_total - no_address), "total": review_total, "pct": _pct(max(0, review_total - no_address), review_total)},
        "has_description": {"count": max(0, review_total - no_description), "total": review_total, "pct": _pct(max(0, review_total - no_description), review_total)},
        "has_opening_hours": {"count": has_hours, "total": hours_total, "pct": _pct(has_hours, hours_total)},
    }
    route_ready_pct = _pct(route_ready, review_total)
    route_breakdown = {key: count for key, count in {
        "missing_opening_hours": values["missing_opening_hours_total"],
        "route_ineligible": values["route_ineligible_total"],
        "missing_canonical_category": values["missing_category_total"],
        "unknown_category": values["unknown_category_total"],
    }.items() if count}
    card_breakdown = {key: count for key, count in {
        "missing_image_url": no_photo,
        "missing_address": values["missing_required_address_total"],
    }.items() if count}
    return {
        "mode": "fast_summary",
        "places_total": values["places_total"],
        "tourist_places": {"total": review_total, "route_ready": route_ready, "route_blocked": route_blockers, "card_ready": card_ready, "card_blocked": card_blockers, "excluded_non_tourist": excluded},
        "route_candidate_total": review_total,
        "route_ready_total": route_ready,
        "route_blockers_total": route_blockers,
        "card_ready_total": card_ready,
        "card_blockers_total": card_blockers,
        "auto_enrichment_total": 0,
        "manual_review_total": manual_review,
        "optional_gaps_total": max(0, values["missing_opening_hours_applicable_total"] - values["missing_opening_hours_total"]),
        "not_applicable_total": excluded,
        "route_blockers_breakdown": route_breakdown,
        "card_blockers_breakdown": card_breakdown,
        "auto_enrichment_queue": {"total": 0, "address_geocoding": 0, "description_generation": 0, "hours_enrichment": 0},
        "manual_review_queue": {"total": manual_review, "pending_photo_review": values["pending_photo_review_total"], "source_conflicts": 0, "low_confidence_critical": 0, "review_queue_open": 0},
        "coverage": coverage,
        "next_actions": [],
        "city_readiness": {
            "route_ready_pct": route_ready_pct,
            "min_route_ready_for_launch": 70.0,
            "is_launch_ready": route_ready_pct >= 70.0 and route_blockers == 0,
            "blocking_reason": None if route_ready_pct >= 70.0 and route_blockers == 0 else "route_ready_pct below threshold or route blockers exist",
        },
    }


def _severity(readiness: int, manual_review_total: int) -> str:
    if readiness >= 90 and manual_review_total == 0:
        return "ok"
    if readiness >= 60:
        return "warning"
    return "critical"


def _todo(rows: list[dict[str, Any]]) -> list[str]:
    critical = [row for row in rows if row["severity"] == "critical"]
    if not critical:
        return []
    return [f"{row['city_name']}: проверить {row['manual_review_total']} мест" for row in critical[:5]]
