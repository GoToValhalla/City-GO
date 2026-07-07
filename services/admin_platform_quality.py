from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.data_quality.constants import STOPLIST_CATEGORIES

NON_TOURIST_LAYERS = {"service_layer", "transport_layer", "admin_evidence_only"}


def city_quality_row(db: Session, city: City, category: str | None = None) -> dict[str, Any]:
    """Return city quality metrics without loading all city places into Python."""
    places_query = db.query(Place).filter(Place.city_id == city.id)
    if category:
        places_query = places_query.filter(Place.category == category)

    tourist = _tourist_review_condition()
    no_photo = tourist & _missing_text(Place.image_url)
    no_address = tourist & _missing_text(Place.address)
    manual_review = no_photo | no_address

    row = places_query.with_entities(
        func.count(Place.id).label("places_total"),
        func.sum(case((tourist, 1), else_=0)).label("review_universe_total"),
        func.sum(case((no_photo, 1), else_=0)).label("no_photo"),
        func.sum(case((no_address, 1), else_=0)).label("no_address"),
        func.sum(case((manual_review, 1), else_=0)).label("manual_review_total"),
    ).one()

    return _build_city_quality_row_from_agg(city, row)


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

    tourist = _tourist_review_condition()
    no_photo = tourist & _missing_text(Place.image_url)
    no_address = tourist & _missing_text(Place.address)
    manual_review = no_photo | no_address

    agg_rows = places_query.with_entities(
        Place.city_id,
        func.count(Place.id).label("places_total"),
        func.sum(case((tourist, 1), else_=0)).label("review_universe_total"),
        func.sum(case((no_photo, 1), else_=0)).label("no_photo"),
        func.sum(case((no_address, 1), else_=0)).label("no_address"),
        func.sum(case((manual_review, 1), else_=0)).label("manual_review_total"),
    ).group_by(Place.city_id).all()

    agg_map = {row.city_id: row for row in agg_rows}

    rows = []
    for city in cities:
        agg_row = agg_map.get(city.id)
        if agg_row is None:
            quality = _empty_city_quality_row(city)
        else:
            quality = _build_city_quality_row_from_agg(city, agg_row)

        coverage = quality["critical_coverage"] if isinstance(quality.get("critical_coverage"), dict) else {}
        row = {
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
        }
        rows.append(row)
    if severity:
        rows = [row for row in rows if row["severity"] == severity]
    return {"items": rows, "total": total_cities if not severity else len(rows), "todo": _todo(rows), "limit": safe_limit, "offset": safe_offset}


def _tourist_review_condition():
    category = func.lower(func.coalesce(Place.canonical_category, Place.category, ""))
    return ~category.in_(tuple(STOPLIST_CATEGORIES)) & ~Place.place_layer.in_(tuple(NON_TOURIST_LAYERS)) & Place.tourist_eligible.is_not(False)


def _missing_text(column):
    return or_(column.is_(None), column == "")


def _build_city_quality_row_from_agg(city: City, agg_row: Any) -> dict[str, Any]:
    places_total = int(agg_row.places_total or 0)
    review_universe_total = int(agg_row.review_universe_total or 0)
    no_photo_total = int(agg_row.no_photo or 0)
    no_address_total = int(agg_row.no_address or 0)
    manual_review_total = int(agg_row.manual_review_total or 0)
    excluded_total = max(0, places_total - review_universe_total)
    blockers = {key: value for key, value in {"no_photo": no_photo_total, "no_address": no_address_total}.items() if value}
    readiness = _readiness_score(review_universe_total, no_photo_total, no_address_total)
    primary_blocker = _primary_blocker(blockers, readiness)
    critical_coverage = _fast_critical_coverage(
        places_total=places_total,
        review_universe_total=review_universe_total,
        manual_review_total=manual_review_total,
        excluded_total=excluded_total,
        no_photo_total=no_photo_total,
        no_address_total=no_address_total,
    )
    return {
        "readiness_score": readiness,
        "stored_readiness_score": int(getattr(city, "readiness_score", 0) or 0),
        "primary_blocker": primary_blocker,
        "blockers": {**blockers, "excluded_by_design": excluded_total},
        "places_total": places_total,
        "review_universe_total": review_universe_total,
        "manual_review_total": manual_review_total,
        "auto_excluded_total": excluded_total,
        "critical_coverage": critical_coverage,
    }


def _empty_city_quality_row(city: City) -> dict[str, Any]:
    return {
        "readiness_score": 0,
        "stored_readiness_score": int(getattr(city, "readiness_score", 0) or 0),
        "primary_blocker": None,
        "blockers": {"excluded_by_design": 0},
        "places_total": 0,
        "review_universe_total": 0,
        "manual_review_total": 0,
        "auto_excluded_total": 0,
        "critical_coverage": _fast_critical_coverage(
            places_total=0, review_universe_total=0, manual_review_total=0,
            excluded_total=0, no_photo_total=0, no_address_total=0
        ),
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
    return None


def _fast_critical_coverage(
    *,
    places_total: int,
    review_universe_total: int,
    manual_review_total: int,
    excluded_total: int,
    no_photo_total: int,
    no_address_total: int,
) -> dict[str, Any]:
    """Return smoke-safe critical coverage counters from aggregate SQL results.

    The full triage engine loads every place and several related tables. That is too
    heavy for the default admin quality list and production smoke. Detailed per-place
    critical coverage remains available through the dedicated critical coverage views.
    """
    ready_total = max(0, review_universe_total - manual_review_total)
    return {
        "mode": "fast_summary",
        "places_total": places_total,
        "route_candidate_total": review_universe_total,
        "route_ready_total": ready_total,
        "route_blockers_total": manual_review_total,
        "card_ready_total": ready_total,
        "card_blockers_total": manual_review_total,
        "auto_enrichment_total": no_photo_total + no_address_total,
        "manual_review_total": manual_review_total,
        "optional_gaps_total": 0,
        "not_applicable_total": excluded_total,
        "blockers_breakdown": {
            "no_photo": no_photo_total,
            "no_address": no_address_total,
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
    return [f"Проверить города с критичным качеством: {len(critical)}"]
