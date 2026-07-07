from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.data_quality.constants import STOPLIST_CATEGORIES
from services.data_quality.critical_coverage import compute_city_critical_coverage

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

    places_total = int(row.places_total or 0)
    review_universe_total = int(row.review_universe_total or 0)
    no_photo_total = int(row.no_photo or 0)
    no_address_total = int(row.no_address or 0)
    manual_review_total = int(row.manual_review_total or 0)
    excluded_total = max(0, places_total - review_universe_total)
    blockers = {key: value for key, value in {"no_photo": no_photo_total, "no_address": no_address_total}.items() if value}
    readiness = _readiness_score(review_universe_total, no_photo_total, no_address_total)
    primary_blocker = _primary_blocker(blockers, readiness)

    try:
        critical_coverage = compute_city_critical_coverage(db, places_query)
    except Exception as exc:  # noqa: BLE001 - admin screen must degrade, not fail
        critical_coverage = {"degraded": True, "error": exc.__class__.__name__}

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


def quality_summary(
    db: Session,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, object]:
    query = db.query(City)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if region:
        query = query.filter(City.region == region)
    total = int(query.count() or 0)
    safe_limit = max(1, min(50, int(limit or 25)))
    safe_offset = max(0, int(offset or 0))
    rows = []
    for city in query.order_by(City.name.asc()).offset(safe_offset).limit(safe_limit).all():
        quality = city_quality_row(db, city, category=category)
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
    return {"items": rows, "total": total if not severity else len(rows), "limit": safe_limit, "offset": safe_offset, "todo": _todo(rows)}


def _tourist_review_condition():
    category = func.lower(func.coalesce(Place.canonical_category, Place.category, ""))
    return ~category.in_(tuple(STOPLIST_CATEGORIES)) & ~Place.place_layer.in_(tuple(NON_TOURIST_LAYERS)) & Place.tourist_eligible.is_not(False)


def _missing_text(column):
    return or_(column.is_(None), column == "")


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
