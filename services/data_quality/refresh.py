"""Refresh persisted data quality issues from deterministic checks."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from core.config import settings
from models.data_quality import DataQualityIssue
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.data_quality.detect import detect_place_issues
from services.data_quality.types import IssueDraft, RefreshSummary


def refresh_data_quality_issues(
    db: Session,
    *,
    city_id: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> RefreshSummary:
    places = _places(db, city_id=city_id, limit=limit)
    counters: Counter[str] = Counter()
    summary = Counter({"scanned": len(places), "created": 0, "updated": 0, "unchanged": 0})
    for place in places:
        drafts = detect_place_issues(
            place,
            source_observations=_source_rows(db, place),
            confidence_fields=_confidence_rows(db, place),
            review_items=_review_rows(db, place),
            confidence_threshold=float(settings.data_quality_low_confidence_threshold),
        )
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
