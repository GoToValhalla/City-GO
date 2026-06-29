from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.data_quality.constants import STOPLIST_CATEGORIES
from services.data_quality.critical_coverage import compute_city_critical_coverage

NON_TOURIST_LAYERS = {"service_layer", "transport_layer", "admin_evidence_only"}


def city_quality_row(db: Session, city: City, category: str | None = None) -> dict[str, Any]:
    places_query = db.query(Place).filter(Place.city_id == city.id)
    if category:
        places_query = places_query.filter(Place.category == category)
    places = places_query.all()
    tourist_places = [place for place in places if _is_tourist_review_place(place)]
    excluded_total = len(places) - len(tourist_places)
    blockers = _blockers(tourist_places)
    readiness = _readiness_score(tourist_places)
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
        "places_total": len(places),
        "review_universe_total": len(tourist_places),
        "manual_review_total": sum(1 for place in tourist_places if _needs_manual_review(place)),
        "auto_excluded_total": excluded_total,
        "critical_coverage": critical_coverage,
    }


def quality_summary(
    db: Session,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict[str, object]:
    query = db.query(City)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if region:
        query = query.filter(City.region == region)
    rows = []
    for city in query.order_by(City.name.asc()).limit(200).all():
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
    return {"items": rows, "total": len(rows), "todo": _todo(rows)}


def _blockers(places: list[Place]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for place in places:
        if not _has_photo(place):
            counter["no_photo"] += 1
        if not _has_address(place):
            counter["no_address"] += 1
    return dict(counter)


def _readiness_score(places: list[Place]) -> int:
    if not places:
        return 0
    scores: list[int] = []
    for place in places:
        score = 100
        if not _has_photo(place):
            score -= 30
        if not _has_address(place):
            score -= 30
        scores.append(max(score, 0))
    return round(sum(scores) / len(scores))


def _primary_blocker(blockers: dict[str, int], readiness: int) -> str | None:
    if readiness >= 100:
        return None
    if blockers.get("no_photo"):
        return "no_photo"
    if blockers.get("no_address"):
        return "no_address"
    return None


def _is_tourist_review_place(place: Place) -> bool:
    category = _category(place)
    if category in STOPLIST_CATEGORIES:
        return False
    if getattr(place, "place_layer", None) in NON_TOURIST_LAYERS:
        return False
    if getattr(place, "tourist_eligible", True) is False:
        return False
    return True


def _needs_manual_review(place: Place) -> bool:
    return not _has_photo(place) or not _has_address(place)


def _has_photo(place: Place) -> bool:
    return bool((getattr(place, "image_url", None) or "").strip())


def _has_address(place: Place) -> bool:
    return bool((getattr(place, "address", None) or "").strip())


def _category(place: Place) -> str:
    return str(getattr(place, "canonical_category", None) or getattr(place, "category", None) or "").strip().lower()


def _severity(readiness: int, manual_review_total: int) -> str:
    if readiness >= 90 and manual_review_total == 0:
        return "ok"
    if readiness >= 60:
        return "warning"
    return "critical"


def _todo(rows: list[dict[str, Any]]) -> list[dict[str, object]]:
    critical = [row for row in rows if row["severity"] == "critical"]
    if not critical:
        return []
    return [{"type": "review_city_quality", "count": len(critical), "label": "Проверить города с критичным качеством"}]
