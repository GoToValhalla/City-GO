"""Admin API for the unified collection and enrichment pipeline."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from schemas.import_pipeline_foundation import (
    FieldConfidenceRead,
    ImportJobStepRead,
    PhotoCandidateActionResponse,
    PipelineRunResponse,
    ResolveReviewRequest,
    ReviewQueueRead,
)
from services.admin_city_import_job_service import queue_city_import_job
from services.import_job_step_service import list_job_steps
from services.place_field_confidence_service import list_field_confidence
from services.place_photo_candidate_service import (
    PhotoCandidateAlreadyDecidedError,
    approve_photo_candidate,
    reject_photo_candidate,
    set_primary_photo_candidate,
)
from services.review_queue_service import list_review_items, resolve_review_item

router = APIRouter(prefix="/admin/place-enrichment", tags=["admin-import-pipeline"])


@router.post("/pipeline/{city_slug}/run", response_model=PipelineRunResponse)
def run_city_pipeline(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    try:
        job = queue_city_import_job(db, city_id=city.id, actor_id=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    return PipelineRunResponse(
        job_id=job.id,
        city_slug=city.slug,
        status="queued",
        message="Полный сбор и обогащение поставлены в очередь. Задачу выполнит import-worker.",
    )


@router.get("/jobs/{job_id}/steps", response_model=list[ImportJobStepRead])
def get_pipeline_steps(
    job_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> list[ImportJobStepRead]:
    return [ImportJobStepRead.model_validate(item) for item in list_job_steps(db, job_id)]


@router.get("/places/{place_id}/confidence", response_model=list[FieldConfidenceRead])
def get_place_confidence(
    place_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> list[FieldConfidenceRead]:
    return [FieldConfidenceRead.model_validate(item) for item in list_field_confidence(db, place_id)]


@router.get("/review-queue", response_model=list[ReviewQueueRead])
def get_review_queue(
    city_slug: str | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> list[ReviewQueueRead]:
    return [ReviewQueueRead.model_validate(item) for item in list_review_items(db, city_slug=city_slug)]


@router.post("/review-queue/{item_id}/resolve", response_model=ReviewQueueRead)
def post_resolve_review_item(
    item_id: int,
    body: ResolveReviewRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> ReviewQueueRead:
    result = resolve_review_item(db, item_id, actor=auth.actor_id, resolution=body.resolution)
    if result.item is None:
        raise HTTPException(status_code=404, detail="Задача проверки не найдена")
    if not result.ok:
        raise HTTPException(status_code=409, detail=f"Задача проверки уже обработана: {result.reason}")
    db.commit()
    return ReviewQueueRead.model_validate(result.item)


@router.post("/photo-candidates/{candidate_id}/approve", response_model=PhotoCandidateActionResponse)
def post_approve_photo_candidate(
    candidate_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PhotoCandidateActionResponse:
    try:
        item = approve_photo_candidate(db, candidate_id, actor=auth.actor_id)
    except PhotoCandidateAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _photo_response(db, item)


@router.post("/photo-candidates/{candidate_id}/reject", response_model=PhotoCandidateActionResponse)
def post_reject_photo_candidate(
    candidate_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PhotoCandidateActionResponse:
    try:
        item = reject_photo_candidate(db, candidate_id, actor=auth.actor_id)
    except PhotoCandidateAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _photo_response(db, item)


@router.post("/photo-candidates/{candidate_id}/set-primary", response_model=PhotoCandidateActionResponse)
def post_primary_photo_candidate(
    candidate_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PhotoCandidateActionResponse:
    try:
        item = set_primary_photo_candidate(db, candidate_id, actor=auth.actor_id)
    except PhotoCandidateAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _photo_response(db, item)


def _photo_response(db: Session, item: object | None) -> PhotoCandidateActionResponse:
    if item is None:
        raise HTTPException(status_code=404, detail="Фото-кандидат не найден")
    db.commit()
    return PhotoCandidateActionResponse.model_validate(item)
