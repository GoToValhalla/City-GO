"""Query helpers and API payloads for data quality issues."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Query, Session

from models.city import City
from models.data_quality import DataQualityIssue
from models.place import Place
from services.admin_platform_quality import city_quality_row
from services.data_quality.constants import ISSUE_POSSIBLE_DUPLICATE, OPEN_STATUSES, SUMMARY_KEYS


def list_data_quality_issues(
    db: Session,
    *,
    filters: dict[str, object],
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    query = _issue_query(db, filters)
    total = query.count()
    issues = query.order_by(DataQualityIssue.last_seen_at.desc(), DataQualityIssue.id.desc()).offset(offset).limit(limit).all()
    return [_issue_payload(db, issue) for issue in issues], total


def list_possible_duplicate_groups(
    db: Session,
    *,
    filters: dict[str, object],
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    duplicate_filters = {**filters, "issue_type": ISSUE_POSSIBLE_DUPLICATE}
    issues = _issue_query(db, duplicate_filters).order_by(
        DataQualityIssue.last_seen_at.desc(), DataQualityIssue.id.desc(),
    ).all()
    groups = _duplicate_groups(db, issues)
    return groups[offset: offset + limit], len(groups)


def build_data_quality_summary(db: Session) -> dict[str, object]:
    rows = db.query(DataQualityIssue.issue_type, DataQualityIssue.city_id).filter(
        DataQualityIssue.status.in_(tuple(OPEN_STATUSES)),
    ).all()
    totals = _totals(rows)
    return {
        "totals": {**totals, "excluded_from_routes": _excluded_from_routes(db), "open_issues": len(rows)},
        "by_city": _city_rows(db, rows),
        "generated_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _issue_query(db: Session, filters: dict[str, object]) -> Query:
    query = db.query(DataQualityIssue)
    if filters.get("city_slug"):
        query = query.join(City, City.id == DataQualityIssue.city_id).filter(City.slug == filters["city_slug"])
    for attr in ("city_id", "issue_type", "severity"):
        if filters.get(attr) is not None:
            query = query.filter(getattr(DataQualityIssue, attr) == filters[attr])
    if filters.get("status") is not None:
        query = query.filter(DataQualityIssue.status == filters["status"])
    else:
        query = query.filter(DataQualityIssue.status.in_(tuple(OPEN_STATUSES)))
    if filters.get("published") is not None or filters.get("route_eligible") is not None:
        query = query.join(Place, Place.id == DataQualityIssue.place_id)
    if filters.get("published") is not None:
        query = query.filter(Place.is_published.is_(bool(filters["published"])))
    if filters.get("route_eligible") is not None:
        query = query.filter(Place.is_route_eligible.is_(bool(filters["route_eligible"])))
    return query


def _issue_payload(db: Session, issue: DataQualityIssue) -> dict[str, object]:
    place = db.query(Place).filter(Place.id == issue.place_id).first() if issue.place_id else None
    city = db.query(City).filter(City.id == issue.city_id).first() if issue.city_id else None
    return {
        "id": issue.id,
        "place_id": issue.place_id,
        "city_id": issue.city_id,
        "issue_type": issue.issue_type,
        "severity": issue.severity,
        "status": issue.status,
        "reason": issue.reason,
        "source": issue.source,
        "evidence": issue.evidence or {},
        "fingerprint": issue.fingerprint,
        "first_seen_at": issue.first_seen_at,
        "last_seen_at": issue.last_seen_at,
        "place": _place_summary(place, city),
    }


def _place_summary(place: Place | None, city: City | None) -> dict[str, object] | None:
    if place is None:
        return None
    return {
        "id": place.id,
        "title": place.title,
        "city": city.name if city else None,
        "city_slug": city.slug if city else None,
        "category": place.category,
        "publication_status": place.publication_status,
        "is_published": place.is_published,
        "is_route_eligible": place.is_route_eligible,
        "has_photo": bool((place.image_url or "").strip()),
        "has_address": bool((place.address or "").strip()),
    }


def _duplicate_groups(db: Session, issues: list[DataQualityIssue]) -> list[dict[str, object]]:
    grouped: dict[str, list[DataQualityIssue]] = {}
    for issue in issues:
        grouped.setdefault(_duplicate_group_key(issue), []).append(issue)

    result = [_duplicate_group_payload(db, key, group) for key, group in grouped.items()]
    return sorted(result, key=lambda row: (str(row["last_seen_at"]), int(row["issues_count"])), reverse=True)


def _duplicate_group_key(issue: DataQualityIssue) -> str:
    evidence = issue.evidence or {}
    normalized = str(evidence.get("normalized_title") or "").strip()
    ids = _duplicate_ids(issue)
    if ids:
        return f"{issue.city_id}:{normalized}:{','.join(str(item) for item in ids)}"
    return f"{issue.city_id}:{normalized}:{issue.reason or issue.fingerprint}"


def _duplicate_group_payload(db: Session, key: str, issues: list[DataQualityIssue]) -> dict[str, object]:
    city = db.query(City).filter(City.id == issues[0].city_id).first() if issues[0].city_id else None
    evidence = _merged_duplicate_evidence(issues)
    place_ids = sorted({place_id for issue in issues for place_id in _duplicate_ids(issue) if place_id is not None})
    if not place_ids:
        place_ids = sorted({issue.place_id for issue in issues if issue.place_id is not None})
    places = db.query(Place).filter(Place.id.in_(place_ids)).order_by(Place.id.asc()).all() if place_ids else []
    return {
        "group_key": key,
        "city_id": issues[0].city_id,
        "city_slug": city.slug if city else None,
        "city_name": city.name if city else None,
        "title": evidence.get("title"),
        "normalized_title": evidence.get("normalized_title"),
        "severity": _max_severity(issue.severity for issue in issues),
        "status_counts": dict(Counter(issue.status for issue in issues)),
        "issues_count": len(issues),
        "issue_ids": sorted(issue.id for issue in issues),
        "place_ids": place_ids,
        "places": [_duplicate_place_payload(place) for place in places],
        "evidence": evidence,
        "first_seen_at": min(issue.first_seen_at for issue in issues),
        "last_seen_at": max(issue.last_seen_at for issue in issues),
    }


def _merged_duplicate_evidence(issues: list[DataQualityIssue]) -> dict[str, object]:
    evidence_rows = [issue.evidence or {} for issue in issues]
    base: dict[str, object] = {}
    for key in ("title", "normalized_title", "duplicate_group_size", "max_distance_meters", "place_category"):
        value = next((row.get(key) for row in evidence_rows if row.get(key) is not None), None)
        if value is not None:
            base[key] = value
    ids = sorted({place_id for issue in issues for place_id in _duplicate_ids(issue) if place_id is not None})
    if ids:
        base["duplicate_place_ids"] = ids
        base["duplicate_group_size"] = len(ids)
    return base


def _duplicate_ids(issue: DataQualityIssue) -> list[int]:
    raw_ids = (issue.evidence or {}).get("duplicate_place_ids") or []
    ids: list[int] = []
    if isinstance(raw_ids, list):
        for raw_id in raw_ids:
            try:
                ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
    if issue.place_id is not None:
        ids.append(issue.place_id)
    return sorted(set(ids))


def _duplicate_place_payload(place: Place) -> dict[str, object]:
    return {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "category": place.category,
        "address": place.address,
        "image_url": place.image_url,
        "lat": place.lat,
        "lng": place.lng,
        "is_published": place.is_published,
        "is_route_eligible": place.is_route_eligible,
        "publication_status": place.publication_status,
        "has_photo": bool((place.image_url or "").strip()),
        "has_address": bool((place.address or "").strip()),
    }


def _max_severity(values: Any) -> str:
    order = {"critical": 4, "high": 3, "warning": 2, "medium": 1, "low": 0}
    severities = [str(value) for value in values]
    if not severities:
        return "warning"
    return max(severities, key=lambda value: order.get(value, 0))


def _totals(rows: list[tuple[str, int | None]]) -> dict[str, int]:
    counter = Counter(issue_type for issue_type, _ in rows)
    return {key: int(counter[issue_type]) for key, issue_type in SUMMARY_KEYS.items()}


def _city_rows(db: Session, rows: list[tuple[str, int | None]]) -> list[dict[str, object]]:
    cities = {city.id: city for city in db.query(City).all()}
    city_ids = sorted({city_id for _, city_id in rows if city_id is not None})
    result: list[dict[str, object]] = []
    for city_id in city_ids:
        city = cities.get(city_id)
        if city is None:
            continue
        quality = city_quality_row(db, city)
        result.append({
            **_city_totals(city_id, rows),
            "coverage_score": quality["readiness_score"],
            "stored_coverage_score": quality["stored_readiness_score"],
            "primary_blocker": quality["primary_blocker"],
            "city_id": city_id,
            "city_slug": city.slug,
            "city_name": city.name,
        })
    return result


def _city_totals(city_id: int, rows: list[tuple[str, int | None]]) -> dict[str, int]:
    return _totals([(issue_type, row_city_id) for issue_type, row_city_id in rows if row_city_id == city_id])


def _excluded_from_routes(db: Session) -> int:
    return db.query(Place).filter(Place.is_published.is_(True), Place.is_route_eligible.is_(False)).count()


def _now_iso() -> str:
    return datetime.utcnow().isoformat()