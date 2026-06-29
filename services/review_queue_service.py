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
    """Create or update one active review issue without violating the open-item key.

    The database allows one open row per ``place_id + field_name + reason``.
    Import/enrichment stages may call this function repeatedly for the same
    issue, or may first create a generic field issue and later normalize it to a
    concrete reason. Always prefer the exact open item before mutating any other
    row; otherwise changing ``reason`` can collide with an already existing row.
    """
    item = _pending_item(db, place_id=place_id, field_name=field_name, reason=reason)
    item = item or _open_item(db, place_id=place_id, field_name=field_name, reason=reason)
    item = item or _pending_item(db, place_id=place_id, field_name=field_name, reason=None)
    item = item or _open_item(db, place_id=place_id, field_name=field_name, reason=None)
    if item is None:
        item = ReviewQueueItem(
            city_id=city_id,
            place_id=place_id,
            field_name=field_name,
            reason=reason,
            status="open",
        )
    item.city_id = city_id
    item.reason = reason
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


def _open_item(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    reason: str | None,
) -> ReviewQueueItem | None:
    query = db.query(ReviewQueueItem).filter_by(place_id=place_id, field_name=field_name, status="open")
    if reason is not None:
        query = query.filter(ReviewQueueItem.reason == reason)
    return query.order_by(ReviewQueueItem.id.asc()).first()


def _pending_item(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    reason: str | None,
) -> ReviewQueueItem | None:
    for pending in db.new:
        if (
            isinstance(pending, ReviewQueueItem)
            and pending.place_id == place_id
            and pending.field_name == field_name
            and pending.status in {None, "open"}
            and (reason is None or pending.reason == reason)
        ):
            return pending
    return None
