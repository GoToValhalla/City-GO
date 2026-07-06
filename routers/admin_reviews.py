from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.data_foundation import EnrichmentTask
from models.place import Place
from models.place_merge_review import PlaceManualOverride, ReviewItem
from schemas.admin_review import ManualOverrideRequest, ReviewDiffRead, ReviewItemRead, ReviewMergeRequest, ReviewRejectRequest, TriggerEnrichRequest
from services.place_data_merge_service import PlaceDataMergeService
from services.place_merge_errors import PlaceMergeError

router = APIRouter(prefix="/admin", tags=["admin-reviews"])


@router.get("/reviews", response_model=list[ReviewItemRead])
def list_reviews(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[ReviewItemRead]:
    items = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(ReviewItem.status == "pending").order_by(ReviewItem.created_at.desc()).limit(100).all()
    return [_read(item, title) for item, title in items]


@router.get("/reviews/{review_id}/diff", response_model=ReviewDiffRead)
def read_review_diff(review_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    item, title = _review_with_title(db, review_id)
    return ReviewDiffRead(**_read(item, title).model_dump(), proposed_diff=item.proposed_diff)


@router.post("/reviews/{review_id}/merge", response_model=ReviewDiffRead)
def merge_review(review_id: int, body: ReviewMergeRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    try:
        item = PlaceDataMergeService().apply_review_item(db, review_id, body.fields_to_apply, auth.actor_id, body.expected_version, body.force_override_protected)
    except PlaceMergeError as exc:
        raise HTTPException(409 if exc.code == "VERSION_MISMATCH" else 422, {"code": exc.code, "message": str(exc)}) from exc
    title = db.get(Place, item.place_id).title
    return ReviewDiffRead(**_read(item, title).model_dump(), proposed_diff=item.proposed_diff)


@router.post("/reviews/{review_id}/reject", response_model=ReviewDiffRead)
def reject_review(review_id: int, body: ReviewRejectRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    try:
        item = PlaceDataMergeService().reject_review_item(db, review_id, auth.actor_id, body.reason)
    except PlaceMergeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
    title = db.get(Place, item.place_id).title
    return ReviewDiffRead(**_read(item, title).model_dump(), proposed_diff=item.proposed_diff)


@router.post("/places/{place_id}/manual-override", response_model=dict[str, object])
def set_manual_override(place_id: int, body: ManualOverrideRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if db.get(Place, place_id) is None:
        raise HTTPException(404, "Место не найдено")
    db.add(PlaceManualOverride(place_id=place_id, field_name=body.field_name, is_protected=body.is_protected, override_value={"value": body.override_value}, set_by=auth.actor_id))
    db.commit()
    return {"status": "ok", "place_id": place_id, "field_name": body.field_name}


@router.post("/places/{place_id}/trigger-enrich", response_model=dict[str, object])
def trigger_enrich(place_id: int, body: TriggerEnrichRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(404, "Место не найдено")
    task = EnrichmentTask(place_id=place_id, city_id=place.city_id, task_type="manual_deterministic_enrichment", status="completed", payload={"changes": body.changes, "source": body.source, "confidence": body.confidence}, updated_at=datetime.now(timezone.utc))
    db.add(task)
    db.commit()
    try:
        return PlaceDataMergeService().merge_from_enrichment_task(db, task.id, actor=auth.actor_id)
    except PlaceMergeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc


def _review_with_title(db: Session, review_id: int) -> tuple[ReviewItem, str]:
    row = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(ReviewItem.id == review_id).first()
    if row is None:
        raise HTTPException(404, "Заявка не найдена")
    return row


def _read(item: ReviewItem, title: str) -> ReviewItemRead:
    return ReviewItemRead(id=item.id, place_id=item.place_id, place_name=title, source=item.source, confidence=item.confidence, status=item.status, reason=item.reason, created_at=item.created_at, place_version_at_creation=item.place_version_at_creation)
