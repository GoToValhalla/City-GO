"""Approval workflow for source-driven changes to previously imported places."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from services.admin_audit_service import write_admin_audit_log
from services.route_eligibility_policy import evaluate_place_route_eligibility

OPEN_STATUS = "open"
RESOLVED_STATUS = "resolved"
PLACE_CHANGE_FIELD = "place_change"
PUBLIC_PLACE_FIELDS = (
    "status",
    "is_active",
    "is_published",
    "is_visible_in_catalog",
    "is_route_eligible",
    "is_searchable",
    "publication_status",
)
RESTORABLE_PLACE_FIELDS = {
    column.name
    for column in Place.__table__.columns
    if column.name not in {"id", "city_id", "created_at", "updated_at"}
}


def list_place_change_reviews(
    db: Session,
    *,
    city_slug: str | None = None,
    status: str = OPEN_STATUS,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    query = (
        db.query(ReviewQueueItem, Place, City)
        .join(Place, Place.id == ReviewQueueItem.place_id)
        .join(City, City.id == ReviewQueueItem.city_id)
        .filter(ReviewQueueItem.field_name == PLACE_CHANGE_FIELD)
        .filter(ReviewQueueItem.status == status)
    )
    if city_slug:
        query = query.filter(City.slug == city_slug)

    total = query.count()
    rows = (
        query.order_by(ReviewQueueItem.created_at.asc(), ReviewQueueItem.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_review_payload(item, place, city) for item, place, city in rows], total


def approve_place_change_review(
    db: Session,
    review_id: int,
    *,
    actor: str,
    reason: str | None = None,
) -> dict[str, object] | None:
    row = _open_review_row(db, review_id)
    if row is None:
        return None
    result = _resolve_place_change_review(db, row, action="approve", actor=actor, reason=reason)
    db.commit()
    return result


def reject_place_change_review(
    db: Session,
    review_id: int,
    *,
    actor: str,
    reason: str | None = None,
) -> dict[str, object] | None:
    row = _open_review_row(db, review_id)
    if row is None:
        return None
    result = _resolve_place_change_review(db, row, action="reject", actor=actor, reason=reason)
    db.commit()
    return result



def bulk_resolve_place_change_reviews(
    db: Session,
    review_ids: list[int],
    *,
    action: str,
    actor: str,
    reason: str | None = None,
) -> tuple[list[dict[str, object]], list[int]]:
    if action not in {"approve", "reject"}:
        raise ValueError("Unsupported place change review action")

    unique_ids = list(dict.fromkeys(review_ids))
    rows = (
        db.query(ReviewQueueItem, Place, City)
        .join(Place, Place.id == ReviewQueueItem.place_id)
        .join(City, City.id == ReviewQueueItem.city_id)
        .filter(
            ReviewQueueItem.id.in_(unique_ids),
            ReviewQueueItem.field_name == PLACE_CHANGE_FIELD,
            ReviewQueueItem.status == OPEN_STATUS,
        )
        .all()
    )
    rows_by_id = {item.id: (item, place, city) for item, place, city in rows}
    resolved = [
        _resolve_place_change_review(db, rows_by_id[review_id], action=action, actor=actor, reason=reason)
        for review_id in unique_ids
        if review_id in rows_by_id
    ]
    db.commit()
    return resolved, [review_id for review_id in unique_ids if review_id not in rows_by_id]


def _resolve_place_change_review(
    db: Session,
    row: tuple[ReviewQueueItem, Place, City],
    *,
    action: str,
    actor: str,
    reason: str | None,
) -> dict[str, object]:
    item, place, city = row
    payload = _payload(item)
    old_value = _place_state(place)

    if action == "approve":
        if payload.get("decision") != "hidden":
            place.status = "active"
            place.is_active = True
            if city.is_active and city.launch_status == "published":
                _publish_place(place, reason=reason)
            else:
                _keep_approved_place_private(place, reason=reason)
        resolution = "approved"
        audit_action = "approve_place_change_review"
    else:
        _restore_previous_place_values(place, payload)
        resolution = "rejected"
        audit_action = "reject_place_change_review"

    _resolve(item, actor=actor, resolution=resolution)
    write_admin_audit_log(
        db,
        actor=actor,
        action=audit_action,
        entity_type="review_queue_item",
        entity_id=item.id,
        old_value=old_value,
        new_value=_place_state(place),
        reason=reason,
    )
    return _review_payload(item, place, city)


def _open_review_row(db: Session, review_id: int) -> tuple[ReviewQueueItem, Place, City] | None:
    return (
        db.query(ReviewQueueItem, Place, City)
        .join(Place, Place.id == ReviewQueueItem.place_id)
        .join(City, City.id == ReviewQueueItem.city_id)
        .filter(
            ReviewQueueItem.id == review_id,
            ReviewQueueItem.field_name == PLACE_CHANGE_FIELD,
            ReviewQueueItem.status == OPEN_STATUS,
        )
        .first()
    )


def _payload(item: ReviewQueueItem) -> dict[str, Any]:
    return dict(item.payload or {})


def _restore_previous_place_values(place: Place, payload: dict[str, Any]) -> None:
    changes = payload.get("changes")
    if isinstance(changes, dict):
        for field_name, change in changes.items():
            if field_name not in RESTORABLE_PLACE_FIELDS or not isinstance(change, dict):
                continue
            if "before" in change:
                setattr(place, field_name, change["before"])

    before_public = payload.get("before_public")
    if isinstance(before_public, dict):
        for field_name in PUBLIC_PLACE_FIELDS:
            if field_name in before_public:
                setattr(place, field_name, before_public[field_name])
    place.updated_at = datetime.utcnow()


def _publish_place(place: Place, *, reason: str | None) -> None:
    now = datetime.utcnow()
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.publication_status = "published"
    verdict = evaluate_place_route_eligibility(place)
    place.is_route_eligible = verdict.eligible
    place.route_exclusion_reason = None if verdict.eligible else ",".join(verdict.reasons[:5])
    place.publication_comment = reason
    place.published_at = now
    place.unpublished_at = None
    place.updated_at = now


def _keep_approved_place_private(place: Place, *, reason: str | None) -> None:
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    place.publication_status = "approved_pending_city_publication"
    place.publication_comment = reason
    place.updated_at = datetime.utcnow()


def _resolve(item: ReviewQueueItem, *, actor: str, resolution: str) -> None:
    item.status = RESOLVED_STATUS
    item.resolved_by = actor
    item.resolved_at = datetime.utcnow()
    item.resolution = resolution
    item.updated_at = datetime.utcnow()


def _review_payload(item: ReviewQueueItem, place: Place, city: City) -> dict[str, object]:
    payload = _payload(item)
    return {
        "id": item.id,
        "city_slug": city.slug,
        "city_name": city.name,
        "place_id": place.id,
        "place_title": place.title,
        "reason": item.reason,
        "severity": item.severity,
        "status": item.status,
        "decision": str(payload.get("decision") or "needs_review"),
        "source": payload.get("source"),
        "source_url": payload.get("source_url"),
        "changes": payload.get("changes") if isinstance(payload.get("changes"), dict) else {},
        "review_reasons": payload.get("review_reasons") if isinstance(payload.get("review_reasons"), list) else [],
        "created_at": item.created_at,
        "resolved_at": item.resolved_at,
        "resolution": item.resolution,
    }


def _place_state(place: Place) -> dict[str, object]:
    return {
        "status": place.status,
        "is_active": bool(place.is_active),
        "is_published": bool(place.is_published),
        "is_visible_in_catalog": bool(place.is_visible_in_catalog),
        "is_searchable": bool(place.is_searchable),
        "is_route_eligible": bool(place.is_route_eligible),
        "publication_status": place.publication_status,
    }
