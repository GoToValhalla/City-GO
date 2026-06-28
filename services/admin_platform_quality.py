"""Cross-city quality dashboard aggregate."""

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.data_quality.constants import STOPLIST_CATEGORIES
from services.data_quality.critical_coverage import compute_city_critical_coverage


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
    rows = [city_quality_row(db, city, category) for city in cities.order_by(City.name).all()]
    filtered = [row for row in rows if not severity or row["severity"] == severity]
    return {
        "items": filtered,
        "total": len(filtered),
        "todo": [
            "Live score считает ручную проверку только по маршруто-релевантным местам.",
            "Stage 1 автопилота уже включён: safe stoplist auto-exclude доступен через preview/apply/rollback.",
            "Quality Rules v2 включён read-only: фото, часы, адреса и описания разложены на route/card/auto/manual корзины.",
            "Следующий шаг: материализовать quality_bucket/snapshot после проверки формулы на реальных городах.",
        ],
    }


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
    critical_coverage = compute_city_critical_coverage(db, query)
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