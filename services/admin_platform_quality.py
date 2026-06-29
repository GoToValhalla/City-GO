"""Cross-city quality dashboard aggregate."""

import logging
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.data_quality.constants import STOPLIST_CATEGORIES
from services.data_quality.critical_coverage import compute_city_critical_coverage

logger = logging.getLogger(__name__)


def quality_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict[str, object]:
    cities = db.query(City)
    if city_slug:
        cities = cities.filter(City.slug == city_slug)
    if region:
        cities = cities.filter(City.region == region)

    try:
        city_rows = cities.order_by(City.name).all()
    except Exception as exc:  # noqa: BLE001 - admin dashboard must degrade instead of returning 500.
        logger.exception("admin_quality_city_query_failed")
        return {
            "items": [],
            "total": 0,
            "todo": _todo_items(),
            "errors": [{"scope": "cities", "reason": exc.__class__.__name__}],
        }

    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for city in city_rows:
        try:
            rows.append(city_quality_row(db, city, category))
        except Exception as exc:  # noqa: BLE001 - isolate bad city rows from the whole dashboard.
            logger.exception("admin_quality_city_row_failed", extra={"city_slug": city.slug})
            rows.append(_degraded_city_row(city, category=category, reason=exc.__class__.__name__))
            errors.append({"city_slug": city.slug, "reason": exc.__class__.__name__})

    filtered = [row for row in rows if not severity or row["severity"] == severity]
    payload: dict[str, object] = {
        "items": filtered,
        "total": len(filtered),
        "todo": _todo_items(),
    }
    if errors:
        payload["errors"] = errors
    return payload


def city_quality_row(db: Session, city: City, category: str | None = None) -> dict[str, object]:
    query = db.query(Place).filter(Place.city_id == city.id)
    if category:
        query = query.filter(Place.category == category)
    total = query.count()
    review_query = _route_review_query(query)
    review_total = review_query.count()
    blockers = {
        "no_photo": review_query.filter(Place.image_url.is_(None)).count(),
        "no_address": review_query.filter(Place.address.is_(None)).count(),
        "low_quality": review_query.filter(Place.quality_score < 50).count(),
        "stale": review_query.filter(Place.verification_status == "needs_recheck").count(),
        "route_ineligible": query.filter(Place.is_route_eligible.is_(False)).count(),
        "excluded_by_design": total - review_total,
    }
    score = _live_quality_score(review_total, blockers)
    severity = "critical" if score < 40 else "warning" if score < 75 else "ok"
    try:
        critical_coverage = compute_city_critical_coverage(db, query)
    except Exception as exc:  # noqa: BLE001 - keep /admin/quality available if deep coverage breaks.
        logger.exception("admin_quality_critical_coverage_failed", extra={"city_slug": city.slug})
        critical_coverage = _empty_critical_coverage(total, reason=exc.__class__.__name__)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "region": city.region,
        "readiness_score": score,
        "stored_readiness_score": int(city.readiness_score or 0),
        "places_total": total,
        "review_universe_total": review_total,
        "manual_review_total": _manual_review_total(review_query),
        "auto_excluded_total": blockers["excluded_by_design"],
        "severity": severity,
        "blockers": blockers,
        "primary_blocker": _primary_blocker(blockers),
        "route_candidate_total": critical_coverage["route_candidate_total"],
        "route_ready_total": critical_coverage["route_ready_total"],
        "route_blockers_total": critical_coverage["route_blockers_total"],
        "card_ready_total": critical_coverage["card_ready_total"],
        "card_blockers_total": critical_coverage["card_blockers_total"],
        "auto_enrichment_total": critical_coverage["auto_enrichment_total"],
        "critical_manual_review_total": critical_coverage["manual_review_total"],
        "optional_gaps_total": critical_coverage["optional_gaps_total"],
        "not_applicable_total": critical_coverage["not_applicable_total"],
        "critical_coverage": critical_coverage,
    }


def _route_review_query(query: Query) -> Query:
    stoplist = tuple(STOPLIST_CATEGORIES)
    return query.filter(and_(
        or_(Place.category.is_(None), ~Place.category.in_(stoplist)),
        or_(Place.canonical_category.is_(None), ~Place.canonical_category.in_(stoplist)),
        Place.is_spam_poi.is_(False),
        ~Place.lifecycle_status.in_(("archived", "deleted", "spam")),
        ~Place.publication_status.in_(("archived", "duplicate_hidden", "rejected")),
    ))


def _live_quality_score(review_total: int, blockers: dict[str, int]) -> int:
    if review_total <= 0:
        return 100
    penalty = (
        35 * _ratio(blockers["no_photo"], review_total)
        + 25 * _ratio(blockers["no_address"], review_total)
        + 20 * _ratio(blockers["low_quality"], review_total)
        + 10 * _ratio(blockers["stale"], review_total)
    )
    # route_ineligible and excluded_by_design are shown as operational counts but
    # are not penalties: excluding pharmacies/banks/services from routes is the
    # correct state, not manual work.
    return max(0, min(100, round(100 - penalty)))


def _manual_review_total(review_query: Query) -> int:
    return review_query.filter(or_(
        Place.image_url.is_(None),
        Place.address.is_(None),
        Place.quality_score < 50,
        Place.verification_status == "needs_recheck",
    )).count()


def _ratio(value: int, total: int) -> float:
    return min(1.0, max(0.0, value / total)) if total else 0.0


def _primary_blocker(blockers: dict[str, int]) -> str | None:
    candidates = {
        key: value
        for key, value in blockers.items()
        if key not in {"route_ineligible", "excluded_by_design"} and value > 0
    }
    if not candidates:
        return None
    return max(candidates, key=candidates.get)


def _todo_items() -> list[str]:
    return [
        "Live score считает ручную проверку только по маршруто-релевантным местам.",
        "Stage 1 автопилота уже включён: safe stoplist auto-exclude доступен через preview/apply/rollback.",
        "Quality Rules v2 включён read-only: фото, часы, адреса и описания разложены на route/card/auto/manual корзины.",
        "Следующий шаг: материализовать quality_bucket/snapshot после проверки формулы на реальных городах.",
    ]


def _degraded_city_row(city: City, *, category: str | None, reason: str) -> dict[str, object]:
    critical_coverage = _empty_critical_coverage(0, reason=reason)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "region": city.region,
        "readiness_score": 0,
        "stored_readiness_score": int(city.readiness_score or 0),
        "places_total": 0,
        "review_universe_total": 0,
        "manual_review_total": 0,
        "auto_excluded_total": 0,
        "severity": "critical",
        "blockers": {
            "no_photo": 0,
            "no_address": 0,
            "low_quality": 0,
            "stale": 0,
            "route_ineligible": 0,
            "excluded_by_design": 0,
            "row_error": 1,
        },
        "primary_blocker": "row_error",
        "route_candidate_total": 0,
        "route_ready_total": 0,
        "route_blockers_total": 0,
        "card_ready_total": 0,
        "card_blockers_total": 0,
        "auto_enrichment_total": 0,
        "critical_manual_review_total": 0,
        "optional_gaps_total": 0,
        "not_applicable_total": 0,
        "critical_coverage": {**critical_coverage, "category": category},
    }


def _empty_critical_coverage(places_total: int, *, reason: str) -> dict[str, Any]:
    return {
        "places_total": places_total,
        "tourist_places": {
            "total": 0,
            "route_ready": 0,
            "route_blocked": 0,
            "card_ready": 0,
            "card_blocked": 0,
            "excluded_non_tourist": 0,
        },
        "route_candidate_total": 0,
        "route_ready_total": 0,
        "route_blockers_total": 0,
        "card_ready_total": 0,
        "card_blockers_total": 0,
        "auto_enrichment_total": 0,
        "manual_review_total": 0,
        "optional_gaps_total": 0,
        "not_applicable_total": 0,
        "route_blockers_breakdown": {},
        "card_blockers_breakdown": {},
        "auto_enrichment_queue": {
            "total": 0,
            "address_geocoding": 0,
            "description_generation": 0,
            "hours_enrichment": 0,
        },
        "manual_review_queue": {
            "total": 0,
            "pending_photo_review": 0,
            "source_conflicts": 0,
            "low_confidence_critical": 0,
            "review_queue_open": 0,
        },
        "coverage": {
            "has_address": {"covered": 0, "total": 0, "pct": 0.0},
            "has_approved_photo": {"covered": 0, "total": 0, "pct": 0.0},
            "has_description": {"covered": 0, "total": 0, "pct": 0.0},
            "has_opening_hours": {"covered": 0, "total": 0, "pct": 0.0},
        },
        "next_actions": [],
        "city_readiness": {
            "route_ready_pct": 0.0,
            "min_route_ready_for_launch": 70.0,
            "is_launch_ready": False,
            "blocking_reason": f"critical coverage unavailable: {reason}",
        },
        "degraded": True,
        "error": reason,
    }
