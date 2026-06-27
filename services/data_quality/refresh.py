"""Refresh persisted data quality issues from deterministic checks."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from core.config import settings
from models.data_quality import DataQualityIssue
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.data_quality.constants import ISSUE_POSSIBLE_DUPLICATE
from services.data_quality.detect import detect_place_issues
from services.data_quality.fingerprint import issue_fingerprint
from services.data_quality.types import IssueDraft, RefreshSummary

DUPLICATE_DISTANCE_METERS = 150.0


def refresh_data_quality_issues(
    db: Session,
    *,
    city_id: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> RefreshSummary:
    places = _places(db, city_id=city_id, limit=limit)
    duplicate_drafts = _group_drafts_by_place(_possible_duplicate_drafts(places))
    counters: Counter[str] = Counter()
    summary = Counter({"scanned": len(places), "created": 0, "updated": 0, "unchanged": 0})
    for place in places:
        drafts = [
            *detect_place_issues(
                place,
                source_observations=_source_rows(db, place),
                confidence_fields=_confidence_rows(db, place),
                review_items=_review_rows(db, place),
                confidence_threshold=float(settings.data_quality_low_confidence_threshold),
            ),
            *duplicate_drafts.get(place.id, []),
        ]
        counters.update(draft.issue_type for draft in drafts)
        if not dry_run:
            summary.update(_persist_drafts(db, drafts))
    if not dry_run:
        db.commit()
    return RefreshSummary(
        scanned=summary["scanned"],
        created=summary["created"],
        updated=summary["updated"],
        unchanged=summary["unchanged"],
        resolved=0,
        by_issue_type=dict(counters),
    )


def upsert_issue(db: Session, draft: IssueDraft) -> tuple[DataQualityIssue, str]:
    now = datetime.utcnow()
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.fingerprint == draft.fingerprint).first()
    if issue is None:
        issue = DataQualityIssue(**draft.__dict__, first_seen_at=now, last_seen_at=now)
        db.add(issue)
        return issue, "created"
    changed = _update_issue(issue, draft, now)
    return issue, "updated" if changed else "unchanged"


def _persist_drafts(db: Session, drafts: list[IssueDraft]) -> Counter[str]:
    results = Counter()
    for draft in drafts:
        _, status = upsert_issue(db, draft)
        results[status] += 1
    return results


def _update_issue(issue: DataQualityIssue, draft: IssueDraft, now: datetime) -> bool:
    before = (issue.severity, issue.status, issue.reason, issue.evidence)
    issue.severity = draft.severity
    issue.reason = draft.reason
    issue.source = draft.source
    issue.evidence = draft.evidence
    issue.last_seen_at = now
    if issue.status == "resolved":
        issue.status = "open"
        issue.resolved_at = None
    return before != (issue.severity, issue.status, issue.reason, issue.evidence)


def _places(db: Session, *, city_id: int | None, limit: int | None) -> list[Place]:
    query = db.query(Place).order_by(Place.id.asc())
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def _source_rows(db: Session, place: Place) -> list[SourceObservation]:
    return db.query(SourceObservation).filter(SourceObservation.canonical_place_id == place.id).all()


def _confidence_rows(db: Session, place: Place) -> list[PlaceFieldConfidence]:
    return db.query(PlaceFieldConfidence).filter(PlaceFieldConfidence.place_id == place.id).all()


def _review_rows(db: Session, place: Place) -> list[ReviewQueueItem]:
    return db.query(ReviewQueueItem).filter(ReviewQueueItem.place_id == place.id).all()


def _group_drafts_by_place(drafts: list[IssueDraft]) -> dict[int | None, list[IssueDraft]]:
    grouped: dict[int | None, list[IssueDraft]] = defaultdict(list)
    for draft in drafts:
        grouped[draft.place_id].append(draft)
    return grouped


def _possible_duplicate_drafts(places: list[Place]) -> list[IssueDraft]:
    by_key: dict[tuple[int, str], list[Place]] = defaultdict(list)
    for place in places:
        normalized = _normalized_title(place.title)
        if normalized and _has_coordinates(place):
            by_key[(place.city_id, normalized)].append(place)

    drafts: list[IssueDraft] = []
    for (city_id, normalized), group in by_key.items():
        if len(group) < 2:
            continue
        for place in group:
            nearby = sorted(
                (
                    other for other in group
                    if other.id != place.id and _distance_meters(place, other) <= DUPLICATE_DISTANCE_METERS
                ),
                key=lambda other: other.id,
            )
            if not nearby:
                continue
            duplicate_ids = sorted({place.id, *(other.id for other in nearby)})
            anchor_id = duplicate_ids[0]
            reason = f"same_title_nearby:{anchor_id}"
            source = "deterministic"
            drafts.append(IssueDraft(
                place_id=place.id,
                city_id=city_id,
                issue_type=ISSUE_POSSIBLE_DUPLICATE,
                severity="warning",
                reason=reason,
                source=source,
                evidence={
                    "title": place.title,
                    "normalized_title": normalized,
                    "duplicate_place_ids": duplicate_ids,
                    "duplicate_group_size": len(duplicate_ids),
                    "max_distance_meters": DUPLICATE_DISTANCE_METERS,
                    "place_category": place.category,
                    "lat": place.lat,
                    "lng": place.lng,
                },
                fingerprint=issue_fingerprint(
                    place_id=place.id,
                    city_id=city_id,
                    issue_type=ISSUE_POSSIBLE_DUPLICATE,
                    reason=reason,
                    source=source,
                ),
            ))
    return drafts


def _normalized_title(value: str | None) -> str | None:
    title = (value or "").casefold().replace("ё", "е")
    title = re.sub(r"[^0-9a-zа-я]+", " ", title).strip()
    if len(title) < 4:
        return None
    return re.sub(r"\s+", " ", title)


def _has_coordinates(place: Place) -> bool:
    return place.lat is not None and place.lng is not None


def _distance_meters(a: Place, b: Place) -> float:
    if not _has_coordinates(a) or not _has_coordinates(b):
        return math.inf
    radius = 6371000.0
    phi1 = math.radians(a.lat)
    phi2 = math.radians(b.lat)
    d_phi = math.radians(b.lat - a.lat)
    d_lam = math.radians(b.lng - a.lng)
    value = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
