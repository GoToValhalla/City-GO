"""Import-safe bounded quality dashboard summary.

This module is intentionally lightweight. The admin quality page must open even
when detailed live quality calculations are too expensive for production.
Heavy coverage calculations belong in materialized snapshots or explicit
city-level drill-down endpoints, not in the cross-city page-load request.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def quality_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict[str, object]:
    from models.city import City

    query = db.query(City)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if region:
        query = query.filter(City.region == region)

    rows = query.order_by(City.name.asc()).limit(200).all()
    items = [_city_row(city, category=category) for city in rows]
    if severity:
        items = [item for item in items if item["severity"] == severity]
    return {"items": items, "total": len(items), "todo": _todo_items()}


def _city_row(city: Any, *, category: str | None) -> dict[str, object]:
    critical_coverage = _empty_critical_coverage(category=category)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "region": city.region,
        "readiness_score": int(city.readiness_score or 0),
        "stored_readiness_score": int(city.readiness_score or 0),
        "places_total": 0,
        "review_universe_total": 0,
        "manual_review_total": 0,
        "auto_excluded_total": 0,
        "severity": "ok",
        "blockers": {
            "no_photo": 0,
            "no_address": 0,
            "low_quality": 0,
            "stale": 0,
            "route_ineligible": 0,
            "excluded_by_design": 0,
        },
        "primary_blocker": None,
        "route_candidate_total": 0,
        "route_ready_total": 0,
        "route_blockers_total": 0,
        "card_ready_total": 0,
        "card_blockers_total": 0,
        "auto_enrichment_total": 0,
        "critical_manual_review_total": 0,
        "optional_gaps_total": 0,
        "not_applicable_total": 0,
        "critical_coverage": critical_coverage,
    }


def _empty_critical_coverage(*, category: str | None = None) -> dict[str, object]:
    return {
        "places_total": 0,
        "category": category,
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
            "blocking_reason": "quality snapshot is not materialized yet",
        },
        "degraded": True,
        "source": "fast_city_quality_stub",
    }


def _todo_items() -> list[str]:
    return [
        "Вкладка качества сейчас открывается через быстрый safe summary без live deep scan.",
        "Реальные quality counts нужно вынести в materialized snapshot, а не считать на открытии страницы.",
        "До snapshot подробная проверка должна идти через городовые drill-down/очереди, а не через общий cross-city запрос.",
    ]
