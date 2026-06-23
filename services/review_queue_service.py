"""Review queue operations for problematic import fields."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.review_queue_item import ReviewQueueItem


def ensure_review_item(
    db: Session,
    *,
    city_id: int,
    place_id: int,
    field_name: str,
    reason: str,
    job_id: int | None = None,
    severity: str = "medium",
    payload: dict[str, object] | None = None,
) -> ReviewQueueItem:
    item = _pending_item(db, place_id=place_id, field_name=field_name, reason=reason)
    item = item or (
        db.query(ReviewQueueItem)
        .filter_by(place_id=place_id, field_name=field_name, reason=reason, status="open")
        .first()
    )
    if item is None:
        item = ReviewQueueItem(city_id=city_id, place_id=place_id, field_name=field_name, reason=reason)
    item.job_id = job_id
    item.severity = severity
    item.payload = payload or {}
    db.add(item)
    return item


def list_review_items(db: Session, *, city_slug: str | None = None, status: str = "open") -> list[ReviewQueueItem]:
    query = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == status)
    if city_slug:
        from models.city import City

        query = query.join(City, City.id == ReviewQueueItem.city_id).filter(City.slug == city_slug)
    return query.order_by(ReviewQueueItem.created_at.asc(), ReviewQueueItem.id.asc()).all()


def resolve_review_item(db: Session, item_id: int, *, actor: str, resolution: str) -> ReviewQueueItem | None:
    item = db.query(ReviewQueueItem).filter(ReviewQueueItem.id == item_id).first()
    if item is None:
        return None
    item.status = "resolved"
    item.resolved_by = actor
    item.resolved_at = datetime.utcnow()
    item.resolution = resolution
    db.add(item)
    return item


def _pending_item(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    reason: str,
) -> ReviewQueueItem | None:
    for pending in db.new:
        if (
            isinstance(pending, ReviewQueueItem)
            and pending.place_id == place_id
            and pending.field_name == field_name
            and pending.reason == reason
            and pending.status in {None, "open"}
        ):
            return pending
    return None
