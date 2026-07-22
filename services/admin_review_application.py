from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.data_foundation import EnrichmentTask
from models.place import Place
from models.place_merge_review import PlaceManualOverride, ReviewItem
from schemas.admin_review import (
    ManualOverrideRequest, ReviewDiffRead, ReviewItemRead, ReviewMergeRequest,
    ReviewRejectRequest, TriggerEnrichRequest,
)
from services.place_data_merge_service import PlaceDataMergeService


def list_pending(db: Session) -> list[ReviewItemRead]:
    rows = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(
        ReviewItem.status == "pending"
    ).order_by(ReviewItem.created_at.desc()).limit(100).all()
    return [_read(item, title) for item, title in rows]


def review_diff(db: Session, review_id: int) -> ReviewDiffRead:
    item, title = _review_with_title(db, review_id)
    return _diff(item, title)


def merge(db: Session, review_id: int, body: ReviewMergeRequest, *, actor: str) -> ReviewDiffRead:
    item = PlaceDataMergeService().apply_review_item(
        db, review_id, body.fields_to_apply, actor, body.expected_version,
        body.force_override_protected,
    )
    return _diff(item, _place_title(db, item.place_id))


def reject(db: Session, review_id: int, body: ReviewRejectRequest, *, actor: str) -> ReviewDiffRead:
    item = PlaceDataMergeService().reject_review_item(db, review_id, actor, body.reason)
    return _diff(item, _place_title(db, item.place_id))


def set_override(
    db: Session, place_id: int, body: ManualOverrideRequest, *, actor: str,
) -> dict[str, object]:
    if db.get(Place, place_id) is None:
        raise LookupError("Место не найдено")
    db.add(PlaceManualOverride(
        place_id=place_id, field_name=body.field_name, is_protected=body.is_protected,
        override_value={"value": body.override_value}, set_by=actor,
    ))
    db.commit()
    return {"status": "ok", "place_id": place_id, "field_name": body.field_name}


def trigger_enrichment(
    db: Session, place_id: int, body: TriggerEnrichRequest, *, actor: str,
) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        raise LookupError("Место не найдено")
    task = EnrichmentTask(
        place_id=place_id, city_id=place.city_id, task_type="manual_deterministic_enrichment",
        status="completed", payload={"changes": body.changes, "source": body.source,
        "confidence": body.confidence}, updated_at=datetime.now(timezone.utc),
    )
    db.add(task); db.commit()
    return PlaceDataMergeService().merge_from_enrichment_task(db, task.id, actor=actor)


def _review_with_title(db: Session, review_id: int) -> tuple[ReviewItem, str]:
    row = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(
        ReviewItem.id == review_id
    ).first()
    if row is None:
        raise LookupError("Заявка не найдена")
    return row


def _place_title(db: Session, place_id: int) -> str:
    place = db.get(Place, place_id)
    if place is None:
        raise LookupError("Место не найдено")
    return str(place.title)


def _diff(item: ReviewItem, title: str) -> ReviewDiffRead:
    return ReviewDiffRead(**_read(item, title).model_dump(), proposed_diff=item.proposed_diff)


def _read(item: ReviewItem, title: str) -> ReviewItemRead:
    return ReviewItemRead(id=item.id, place_id=item.place_id, place_name=title, source=item.source,
        confidence=item.confidence, status=item.status, reason=item.reason, created_at=item.created_at,
        place_version_at_creation=item.place_version_at_creation)
