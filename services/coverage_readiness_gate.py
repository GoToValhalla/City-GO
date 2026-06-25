from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.known_missing_poi import KnownMissingPoi
from services.coverage_gap_service import CRITICAL_POLICIES, MATCHED_STATUSES

READY_SCORE_CAP_WITH_CRITICAL_GAPS = 69


def apply_coverage_readiness_gate(db: Session, *, city_slug: str | None = None) -> dict[str, Any]:
    """Applies city-level readiness cap when critical coverage rows are unresolved.

    The regular readiness scorer still calculates technical quality from places. This gate adds
    the missing coverage rule: a city with unresolved critical expected POI cannot stay `ready`.
    It is intentionally called after coverage refresh and after import jobs.
    """

    query = db.query(KnownMissingPoi).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)

    critical_by_city: dict[int, int] = defaultdict(int)
    for row in query.all():
        if row.expected_route_policy in CRITICAL_POLICIES and row.status not in MATCHED_STATUSES:
            critical_by_city[int(row.city_id)] += 1

    affected: list[dict[str, Any]] = []
    if not critical_by_city:
        return {"affected": affected, "affected_count": 0}

    cities = db.query(City).filter(City.id.in_(critical_by_city.keys())).all()
    for city in cities:
        previous_score = int(city.readiness_score or 0)
        previous_status = city.quality_status
        if previous_score > READY_SCORE_CAP_WITH_CRITICAL_GAPS:
            city.readiness_score = READY_SCORE_CAP_WITH_CRITICAL_GAPS
        if city.quality_status == "ready":
            city.quality_status = "needs_review"
        affected.append(
            {
                "city_slug": city.slug,
                "critical_unresolved": critical_by_city[int(city.id)],
                "previous_score": previous_score,
                "current_score": int(city.readiness_score or 0),
                "previous_status": previous_status,
                "current_status": city.quality_status,
            }
        )

    db.flush()
    return {"affected": affected, "affected_count": len(affected)}
