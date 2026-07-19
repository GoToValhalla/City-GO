"""Approval workflow for source-driven changes to previously imported places."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from core.publication_state_ownership import PUBLICATION_OWNED_FIELDS
from models.city import City
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from services.admin_audit_service import write_admin_audit_log
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.publication_policy import run_hard_gates
from services.publication_state_writer import (
    REASON_CITY_PUBLICATION_QUALITY_GATE,
    REASON_POLICY_GATE_FAILED,
    REASON_REPAIR_STATE,
    transition_place_publication,
)
from services.review_queue_service import ensure_review_item

OPEN_STATUS = "open"
RESOLVED_STATUS = "resolved"
PLACE_CHANGE_FIELD = "place_change"
PROTECTED_PUBLICATION_FIELDS = PUBLICATION_OWNED_FIELDS
RESTORABLE_PLACE_FIELDS = {
    column.name
    for column in Place.__table__.columns
    if column.name not in {"id", "city_id", "created_at", "updated_at"}
    and column.name not in PROTECTED_PUBLICATION_FIELDS
}


def propose_place_change(
    db: Session,
    *,
    place: Place,
    proposed: dict[str, Any],
    reason: str,
    city_id: int | None = None,
    job_id: int | None = None,
    severity: str = "medium",
) -> bool:
    if not place.is_published:
        return True
    changes = {
        field: {"before": getattr(place, field), "after": value}
        for field, value in proposed.items()
        if field in RESTORABLE_PLACE_FIELDS and getattr(place, field) != value
    }
    if not changes:
        return False
    ensure_review_item(
        db,
        city_id=city_id if city_id is not None else place.city_id,
        place_id=place.id,
        job_id=job_id,
        field_name=PLACE_CHANGE_FIELD,
        reason=reason,
        severity=severity,
        payload={
            "kind": "place_change",
            "applied": False,
            "place_title": place.title,
            "changes": changes,
        },
    )
    return False


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
        .offset(offset).limit(limit).all()
    )
    return [_review_payload(item, place, city) for item, place, city in rows], total


def approve_place_change_review(
    db: Session, review_id: int, *, actor: str, reason: str | None = None
) -> dict[str, object] | None:
    return _resolve_one(db, review_id, action="approve", actor=actor, reason=reason)


def reject_place_change_review(
    db: Session, review_id: int, *, actor: str, reason: str | None = None
) -> dict[str, object] | None:
    return _resolve_one(db, review_id, action="reject", actor=actor, reason=reason)


def _resolve_one(
    db: Session, review_id: int, *, action: str, actor: str, reason: str | None
) -> dict[str, object] | None:
    row = _open_review_row(db, review_id)
    if row is None:
        return None
    try:
        result = _resolve_place_change_review(db, row, action=action, actor=actor, reason=reason)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


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
        .order_by(Place.id.asc(), ReviewQueueItem.id.asc())
        .with_for_update().populate_existing().all()
    )
    rows_by_id = {item.id: (item, place, city) for item, place, city in rows}
    try:
        resolved = [
            _resolve_place_change_review(
                db, rows_by_id[review_id], action=action, actor=actor, reason=reason
            )
            for review_id in unique_ids
            if review_id in rows_by_id
        ]
        db.commit()
        return resolved, [review_id for review_id in unique_ids if review_id not in rows_by_id]
    except Exception:
        db.rollback()
        raise


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
    blocked_gates: list[str] = []

    if action == "approve":
        _apply_pending_changes(place, payload)
        if payload.get("decision") == "hidden":
            _keep_approved_place_private(
                db, place, actor=actor, reason=reason,
                blocked_gates=["review_decision_hidden"],
            )
        else:
            place.status = "active"
            if city.is_active and city.launch_status == "published":
                blocked_gates = run_hard_gates(place, city=city)
                if blocked_gates:
                    _keep_approved_place_private(
                        db, place, actor=actor, reason=reason,
                        blocked_gates=blocked_gates,
                    )
                else:
                    apply_admin_city_publication_place(
                        db, place, actor=actor, source="place_change_review",
                        reason=reason, lock_place=False,
                    )
            else:
                _defer_until_city_publication(
                    db, place, actor=actor, reason=reason, city=city
                )
        resolution = "approved"
        audit_action = "approve_place_change_review"
    else:
        _restore_previous_place_values(db, place, payload, actor=actor, reason=reason)
        resolution = "rejected"
        audit_action = "reject_place_change_review"

    _resolve(item, actor=actor, resolution=resolution)
    write_admin_audit_log(
        db, actor=actor, action=audit_action, entity_type="review_queue_item",
        entity_id=item.id, old_value=old_value, new_value=_place_state(place),
        reason=reason,
    )
    return _review_payload(item, place, city, blocked_gates=blocked_gates)


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
        .order_by(Place.id.asc(), ReviewQueueItem.id.asc())
        .with_for_update().populate_existing().first()
    )


def _payload(item: ReviewQueueItem) -> dict[str, Any]:
    return dict(item.payload or {})


def _apply_pending_changes(place: Place, payload: dict[str, Any]) -> None:
    if payload.get("applied") is not False:
        return
    changes = payload.get("changes")
    if not isinstance(changes, dict):
        return
    for field, change in changes.items():
        if field in RESTORABLE_PLACE_FIELDS and isinstance(change, dict) and "after" in change:
            setattr(place, field, change["after"])


def _restore_previous_place_values(
    db: Session,
    place: Place,
    payload: dict[str, Any],
    *,
    actor: str,
    reason: str | None,
) -> None:
    changes = payload.get("changes")
    if isinstance(changes, dict):
        for field, change in changes.items():
            if field in RESTORABLE_PLACE_FIELDS and isinstance(change, dict) and "before" in change:
                setattr(place, field, change["before"])

    before_public = payload.get("before_public")
    if not isinstance(before_public, dict):
        place.updated_at = datetime.utcnow()
        return
    target_status = str(before_public.get("publication_status") or "draft")
    details = {
        "review_action": "reject",
        "restored_from_review_payload": True,
        "original_publication_status": target_status,
    }
    if bool(before_public.get("is_published")) and target_status == "published":
        apply_admin_city_publication_place(
            db, place, actor=actor, source="place_change_review_restore",
            reason=reason, lock_place=False,
        )
        return
    allowed = {
        "draft", "auto_backlog", "low_confidence", "needs_review",
        "needs_manual_review", "deferred", "hidden", "unpublished", "rejected",
    }
    if target_status not in allowed:
        target_status = "draft"
        details["unknown_original_status"] = True
    transition_place_publication(
        db, place, to_status=target_status, reason_code=REASON_REPAIR_STATE,
        actor=actor, source="place_change_review_restore", reason_details=details,
        human_comment=reason, lock_place=False,
    )


def _keep_approved_place_private(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str | None,
    blocked_gates: list[str],
) -> None:
    transition_place_publication(
        db, place, to_status="needs_review", reason_code=REASON_POLICY_GATE_FAILED,
        actor=actor, source="place_change_review",
        reason_details={"blocked_gates": list(blocked_gates)},
        human_comment=reason, lock_place=False,
    )


def _defer_until_city_publication(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str | None,
    city: City,
) -> None:
    transition_place_publication(
        db, place, to_status="deferred",
        reason_code=REASON_CITY_PUBLICATION_QUALITY_GATE,
        actor=actor, source="place_change_review",
        reason_details={
            "city_id": city.id,
            "city_launch_status": city.launch_status,
            "city_is_active": bool(city.is_active),
        },
        human_comment=reason, lock_place=False,
    )


def _resolve(item: ReviewQueueItem, *, actor: str, resolution: str) -> None:
    item.status = RESOLVED_STATUS
    item.resolved_by = actor
    item.resolved_at = datetime.utcnow()
    item.resolution = resolution
    item.updated_at = datetime.utcnow()


def _review_payload(
    item: ReviewQueueItem,
    place: Place,
    city: City,
    *,
    blocked_gates: list[str] | None = None,
) -> dict[str, object]:
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
        "blocked_by_publication_gate": list(blocked_gates) if blocked_gates else [],
    }


def _place_state(place: Place) -> dict[str, object]:
    return {
        "status": place.status,
        "is_active": bool(place.is_active),
        "is_published": bool(place.is_published),
        "is_visible_in_catalog": bool(place.is_visible_in_catalog),
        "is_searchable": bool(place.is_searchable),
        "is_route_eligible": bool(place.is_route_eligible),
        "route_exclusion_reason": place.route_exclusion_reason,
        "publication_status": place.publication_status,
        "publication_reason_code": place.publication_reason_code,
    }
