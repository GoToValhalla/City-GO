"""Fast data-quality summary for admin read paths.

This module avoids the old request-path pattern where the summary loaded all
issues and then called city quality aggregation for every city. It only performs
bounded aggregate queries and uses stored city readiness for the city rows.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.data_quality import DataQualityIssue
from models.place import Place
from services.data_quality.constants import OPEN_STATUSES, SUMMARY_KEYS

SummaryRow = tuple[str, int | None, int]


def build_data_quality_summary(db: Session) -> dict[str, object]:
    rows: list[SummaryRow] = [
        (str(issue_type), city_id, int(count or 0))
        for issue_type, city_id, count in db.query(
            DataQualityIssue.issue_type,
            DataQualityIssue.city_id,
            func.count(DataQualityIssue.id),
        )
        .filter(DataQualityIssue.status.in_(tuple(OPEN_STATUSES)))
        .group_by(DataQualityIssue.issue_type, DataQualityIssue.city_id)
        .all()
    ]
    totals = _totals(rows)
    open_issues = sum(count for _, _, count in rows)
    return {
        "totals": {**totals, "excluded_from_routes": _excluded_from_routes(db), "open_issues": open_issues},
        "by_city": _city_rows(db, rows),
        "generated_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _totals(rows: list[SummaryRow]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for issue_type, _, count in rows:
        counter[issue_type] += count
    return {key: int(counter[issue_type]) for key, issue_type in SUMMARY_KEYS.items()}


def _city_rows(db: Session, rows: list[SummaryRow]) -> list[dict[str, object]]:
    city_ids = sorted({city_id for _, city_id, _ in rows if city_id is not None})
    if not city_ids:
        return []
    cities = {city.id: city for city in db.query(City).filter(City.id.in_(city_ids)).all()}
    result: list[dict[str, object]] = []
    for city_id in city_ids:
        city = cities.get(city_id)
        if city is None:
            continue
        totals = _city_totals(city_id, rows)
        result.append(
            {
                **totals,
                "coverage_score": int(getattr(city, "readiness_score", 0) or 0),
                "stored_coverage_score": int(getattr(city, "readiness_score", 0) or 0),
                "primary_blocker": _primary_issue(totals),
                "city_id": city_id,
                "city_slug": city.slug,
                "city_name": city.name,
            }
        )
    return result


def _city_totals(city_id: int, rows: list[SummaryRow]) -> dict[str, int]:
    return _totals([(issue_type, row_city_id, count) for issue_type, row_city_id, count in rows if row_city_id == city_id])


def _primary_issue(totals: dict[str, int]) -> str | None:
    ordered = (
        "published_without_photo",
        "without_address",
        "requires_review",
        "low_confidence",
        "route_eligibility_suspicious",
        "possible_duplicates",
    )
    return next((key for key in ordered if totals.get(key, 0) > 0), None)


def _excluded_from_routes(db: Session) -> int:
    return int(db.query(func.count(Place.id)).filter(Place.is_published.is_(True), Place.is_route_eligible.is_(False)).scalar() or 0)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()
