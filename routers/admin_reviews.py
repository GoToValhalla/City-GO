from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_review import ManualOverrideRequest, ReviewDiffRead, ReviewItemRead, ReviewMergeRequest, ReviewRejectRequest, TriggerEnrichRequest
from services.admin_review_application import list_pending, merge, reject, review_diff, set_override, trigger_enrichment
from services.place_merge_errors import PlaceMergeError

router = APIRouter(prefix="/admin", tags=["admin-reviews"])


@router.get("/reviews", response_model=list[ReviewItemRead])
def list_reviews(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[ReviewItemRead]:
    return list_pending(db)


@router.get("/reviews/{review_id}/diff", response_model=ReviewDiffRead)
def read_review_diff(review_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    try:
        return review_diff(db, review_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/reviews/{review_id}/merge", response_model=ReviewDiffRead)
def merge_review(review_id: int, body: ReviewMergeRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    try:
        return merge(db, review_id, body, actor=auth.actor_id)
    except PlaceMergeError as exc:
        raise HTTPException(409 if exc.code == "VERSION_MISMATCH" else 422, {"code": exc.code, "message": str(exc)}) from exc


@router.post("/reviews/{review_id}/reject", response_model=ReviewDiffRead)
def reject_review(review_id: int, body: ReviewRejectRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ReviewDiffRead:
    try:
        return reject(db, review_id, body, actor=auth.actor_id)
    except PlaceMergeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc


@router.post("/places/{place_id}/manual-override", response_model=dict[str, object])
def set_manual_override(place_id: int, body: ManualOverrideRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return set_override(db, place_id, body, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/places/{place_id}/trigger-enrich", response_model=dict[str, object])
def trigger_enrich(place_id: int, body: TriggerEnrichRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        return trigger_enrichment(db, place_id, body, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PlaceMergeError as exc:
        raise HTTPException(422, {"code": exc.code, "message": str(exc)}) from exc
