"""Fast cross-city quality dashboard aggregate."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


QUALITY_SQL = """
SELECT
    cities.slug AS city_slug,
    cities.name AS city_name,
    cities.region AS region,
    COALESCE(cities.readiness_score, 0) AS stored_readiness_score,
    COUNT(places.id) AS places_total,
    SUM(CASE WHEN places.id IS NOT NULL THEN 1 ELSE 0 END) AS review_universe_total,
    SUM(CASE WHEN places.id IS NOT NULL AND places.image_url IS NULL THEN 1 ELSE 0 END) AS no_photo,
    SUM(CASE WHEN places.id IS NOT NULL AND places.address IS NULL THEN 1 ELSE 0 END) AS no_address,
    SUM(CASE WHEN places.id IS NOT NULL AND COALESCE(places.quality_score, 0) < 50 THEN 1 ELSE 0 END) AS low_quality,
    SUM(CASE WHEN places.id IS NOT NULL AND places.verification_status = 'needs_recheck' THEN 1 ELSE 0 END) AS stale,
    SUM(CASE WHEN places.id IS NOT NULL AND places.is_route_eligible = false THEN 1 ELSE 0 END) AS route_ineligible
FROM cities
LEFT JOIN places ON places.city_id = cities.id {category_filter}
WHERE (:city_slug IS NULL OR cities.slug = :city_slug)
  AND (:region IS NULL OR cities.region = :region)
GROUP BY cities.id, cities.slug, cities.name, cities.region, cities.readiness_score
ORDER BY cities.name ASC
"""


def quality_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict[str, object]:
    sql = QUALITY_SQL.format(category_filter="AND places.category = :category" if category else "")
    rows = db.execute(text(sql), {"city_slug": city_slug, "region": region, "category": category}).mappings().all()
    items = [_quality_row(row) for row in rows]
    if severity:
        items = [item for item in items if item["severity"] == severity]
    return {"items": items, "total": len(items), "todo": _todo_items()}


def _quality_row(row) -> dict[str, object]:
    total = _int(row["places_total"])
    review_total = _int(row["review_universe_total"])
    blockers = {
        "no_photo": _int(row["no_photo"]),
        "no_address": _int(row["no_address"]),
        "low_quality": _int(row["low_quality"]),
        "stale": _int(row["stale"]),
        "route_ineligible": _int(row["route_ineligible"]),
        "excluded_by_design": max(0, total - review_total),
    }
    manual = blockers["low_quality"] + blockers["stale"]
    auto_enrichment = blockers["no_photo"] + blockers["no_address"]
    route_blockers = blockers["low_quality"] + blockers["stale"] + blockers["no_address"]
    card_blockers = blockers["no_photo"] + blockers["no_address"]
    route_ready = max(0, review_total - route_blockers)
    score = _score(review_total, blockers)
    severity = "critical" if score < 40 else "warning" if score < 75 else "ok"
    return {
        "city_slug": row["city_slug"],
        "city_name": row["city_name"],
        "region": row["region"],
        "readiness_score": score,
        "stored_readiness_score": _int(row["stored_readiness_score"]),
        "places_total": total,
        "review_universe_total": review_total,
        "manual_review_total": manual,
        "auto_excluded_total": blockers["excluded_by_design"],
        "severity": severity,
        "blockers": blockers,
        "primary_blocker": _primary_blocker(blockers),
        "route_candidate_total": review_total,
        "route_ready_total": route_ready,
        "route_blockers_total": route_blockers,
        "card_ready_total": max(0, review_total - card_blockers),
        "card_blockers_total": card_blockers,
        "auto_enrichment_total": auto_enrichment,
        "critical_manual_review_total": manual,
        "optional_gaps_total": 0,
        "not_applicable_total": blockers["excluded_by_design"],
        "critical_coverage": _coverage_payload(
            places_total=total,
            review_total=review_total,
            route_ready=route_ready,
            route_blockers=route_blockers,
            card_blockers=card_blockers,
            auto_enrichment=auto_enrichment,
            manual=manual,
        ),
    }


def _coverage_payload(*, places_total: int, review_total: int, route_ready: int, route_blockers: int, card_blockers: int, auto_enrichment: int, manual: int) -> dict[str, object]:
    return {
        "places_total": places_total,
        "tourist_places": {
            "total": review_total,
            "route_ready": route_ready,
            "route_blocked": route_blockers,
            "card_ready": max(0, review_total - card_blockers),
            "card_blocked": card_blockers,
            "excluded_non_tourist": max(0, places_total - review_total),
        },
        "route_candidate_total": review_total,
        "route_ready_total": route_ready,
        "route_blockers_total": route_blockers,
        "card_ready_total": max(0, review_total - card_blockers),
        "card_blockers_total": card_blockers,
        "auto_enrichment_total": auto_enrichment,
        "manual_review_total": manual,
        "optional_gaps_total": 0,
        "not_applicable_total": max(0, places_total - review_total),
        "route_blockers_breakdown": {},
        "card_blockers_breakdown": {},
        "auto_enrichment_queue": {
            "total": auto_enrichment,
            "address_geocoding": blockers_zero(),
            "description_generation": blockers_zero(),
            "hours_enrichment": blockers_zero(),
        },
        "manual_review_queue": {
            "total": manual,
            "pending_photo_review": 0,
            "source_conflicts": 0,
            "low_confidence_critical": 0,
            "review_queue_open": manual,
        },
        "coverage": {
            "has_address": _metric(max(0, review_total - route_blockers), review_total),
            "has_approved_photo": _metric(max(0, review_total - card_blockers), review_total),
            "has_description": _metric(max(0, review_total - manual), review_total),
            "has_opening_hours": _metric(0, review_total),
        },
        "next_actions": [],
        "city_readiness": {
            "route_ready_pct": _pct(route_ready, review_total),
            "min_route_ready_for_launch": 70.0,
            "is_launch_ready": _pct(route_ready, review_total) >= 70.0,
            "blocking_reason": None if _pct(route_ready, review_total) >= 70.0 else "route coverage below threshold",
        },
        "degraded": False,
        "source": "fast_quality_summary",
    }


def blockers_zero() -> int:
    return 0


def _score(review_total: int, blockers: dict[str, int]) -> int:
    if review_total <= 0:
        return 100
    penalty = 35 * _ratio(blockers["no_photo"], review_total) + 25 * _ratio(blockers["no_address"], review_total) + 20 * _ratio(blockers["low_quality"], review_total) + 10 * _ratio(blockers["stale"], review_total)
    return max(0, min(100, round(100 - penalty)))


def _primary_blocker(blockers: dict[str, int]) -> str | None:
    candidates = {key: value for key, value in blockers.items() if key not in {"route_ineligible", "excluded_by_design"} and value > 0}
    return max(candidates, key=candidates.get) if candidates else None


def _metric(covered: int, total: int) -> dict[str, object]:
    return {"covered": covered, "total": total, "pct": _pct(covered, total)}


def _pct(value: int, total: int) -> float:
    return round((value / total) * 100, 1) if total else 0.0


def _ratio(value: int, total: int) -> float:
    return min(1.0, max(0.0, value / total)) if total else 0.0


def _int(value) -> int:
    return int(value or 0)


def _todo_items() -> list[str]:
    return [
        "Вкладка качества переведена на быстрый bounded summary без deep scan при открытии.",
        "Тяжёлый critical coverage должен открываться только drill-down запросом по конкретному городу/корзине.",
        "Следующий шаг: materialized quality snapshot для историчности и трендов.",
    ]
