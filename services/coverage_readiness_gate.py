from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.known_missing_poi import KnownMissingPoi
from services.coverage_gap_service import CRITICAL_POLICIES, MATCHED_STATUSES
from services.city_readiness.score import compute_city_readiness_for_city
from services.data_coverage_assurance import build_acceptance

READY_SCORE_CAP_WITH_CRITICAL_GAPS = 69


def apply_coverage_readiness_gate(db: Session, *, city_slug: str | None = None) -> dict[str, Any]:
    """Applies or clears the city-level readiness cap after coverage reconciliation.

    City readiness is blocked not only by raw unresolved rows, but also by the
    Data Coverage Assurance acceptance verdict: low must-have coverage, missing
    explanations or blocking reasons keep the city in needs_review.
    """

    query = db.query(KnownMissingPoi).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)

    rows = query.all()
    critical_by_city: dict[int, int] = defaultdict(int)
    city_ids: set[int] = set()
    for row in rows:
        city_ids.add(int(row.city_id))
        if row.expected_route_policy in CRITICAL_POLICIES and row.status not in MATCHED_STATUSES:
            critical_by_city[int(row.city_id)] += 1

    affected: list[dict[str, Any]] = []
    if not city_ids:
        return {"affected": affected, "affected_count": 0}

    acceptance_by_slug = build_acceptance(rows)
    cities = db.query(City).filter(City.id.in_(city_ids)).all()
    for city in cities:
        previous_score = int(city.readiness_score or 0)
        previous_status = city.quality_status
        critical_unresolved = critical_by_city.get(int(city.id), 0)
        acceptance = acceptance_by_slug.get(city.slug)
        accepted = bool(acceptance.get("accepted")) if acceptance else critical_unresolved == 0

        if critical_unresolved > 0 or not accepted:
            if previous_score > READY_SCORE_CAP_WITH_CRITICAL_GAPS:
                city.readiness_score = READY_SCORE_CAP_WITH_CRITICAL_GAPS
            if city.quality_status == "ready":
                city.quality_status = "needs_review"
        else:
            payload = compute_city_readiness_for_city(db, city=city)
            city.readiness_score = int(payload.get("readiness_score") or 0)
            city.quality_status = str(payload.get("status") or "not_ready")

        affected.append(
            {
                "city_slug": city.slug,
                "critical_unresolved": critical_unresolved,
                "coverage_accepted": accepted,
                "coverage_reasons": list(acceptance.get("reasons") or []) if acceptance else [],
                "previous_score": previous_score,
                "current_score": int(city.readiness_score or 0),
                "previous_status": previous_status,
                "current_status": city.quality_status,
            }
        )

    db.flush()
    return {"affected": affected, "affected_count": len(affected)}
