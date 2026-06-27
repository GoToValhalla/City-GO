"""Admin API for controlled AI task selection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_ai import (
    AICandidateRead,
    AICandidateResolveRequest,
    AIEstimateRequest,
    AIEstimateResponse,
    AIProviderRead,
    AITaskRead,
    AITaskRunDetailRead,
    AITaskRunRead,
    AITaskRunRequest,
)
from services.ai.task_registry import allowed_providers_for_task, provider_specs, task_specs
from services.ai.task_runner import (
    estimate_task,
    get_task_run,
    list_candidates,
    list_candidates_for_task_run,
    list_task_runs,
    resolve_candidate,
    run_task,
)

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


@router.get("/tasks", response_model=list[AITaskRead])
def get_ai_tasks(auth: AdminContext = Depends(admin_required)) -> list[AITaskRead]:
    return [
        AITaskRead(
            key=item.key,
            label=item.label,
            description=item.description,
            mode=item.mode,
            schema_version=item.schema_version,
            enabled=item.enabled,
            allowed_provider_keys=list(item.allowed_provider_keys),
            max_batch_size=item.max_batch_size,
            writes_public_fields=item.writes_public_fields,
            disabled_reason=item.disabled_reason,
        )
        for item in task_specs().values()
    ]


@router.get("/tasks/{task_type}/providers", response_model=list[AIProviderRead])
def get_ai_task_providers(task_type: str, auth: AdminContext = Depends(admin_required)) -> list[AIProviderRead]:
    try:
        providers = allowed_providers_for_task(task_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [AIProviderRead(**provider.__dict__) for provider in providers]


@router.get("/providers", response_model=list[AIProviderRead])
def get_ai_providers(auth: AdminContext = Depends(admin_required)) -> list[AIProviderRead]:
    return [AIProviderRead(**provider.__dict__) for provider in provider_specs().values()]


@router.post("/estimate", response_model=AIEstimateResponse)
def post_ai_estimate(
    body: AIEstimateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AIEstimateResponse:
    try:
        result = estimate_task(
            db,
            task_type=body.task_type,
            provider_key=body.provider_key,
            review_queue_item_id=body.review_queue_item_id,
            place_id=body.place_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AIEstimateResponse(**result)


@router.post("/task-runs", response_model=AITaskRunRead)
def post_ai_task_run(
    body: AITaskRunRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AITaskRunRead:
    if not body.confirm_estimate:
        raise HTTPException(status_code=400, detail="confirm_estimate_required")
    try:
        task_run = run_task(
            db,
            actor=auth.actor_id,
            task_type=body.task_type,
            provider_key=body.provider_key,
            review_queue_item_id=body.review_queue_item_id,
            place_id=body.place_id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(task_run)
    return AITaskRunRead.model_validate(task_run)


@router.get("/task-runs", response_model=list[AITaskRunRead])
def get_ai_task_runs(
    limit: int = Query(default=50, ge=1, le=100),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> list[AITaskRunRead]:
    return [AITaskRunRead.model_validate(item) for item in list_task_runs(db, limit=limit)]


@router.get("/task-runs/{task_run_id}", response_model=AITaskRunDetailRead)
def get_ai_task_run_detail(
    task_run_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AITaskRunDetailRead:
    task_run = get_task_run(db, task_run_id=task_run_id)
    if task_run is None:
        raise HTTPException(status_code=404, detail="AI task run not found")
    detail = AITaskRunDetailRead.model_validate(task_run)
    detail.candidates = [AICandidateRead.model_validate(item) for item in list_candidates_for_task_run(db, task_run_id=task_run_id)]
    return detail


@router.get("/candidates", response_model=list[AICandidateRead])
def get_ai_candidates(
    status: str = "pending",
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> list[AICandidateRead]:
    return [AICandidateRead.model_validate(item) for item in list_candidates(db, status=status)]


@router.post("/candidates/{candidate_id}/accept", response_model=AICandidateRead)
def post_accept_ai_candidate(
    candidate_id: int,
    body: AICandidateResolveRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AICandidateRead:
    return _resolve(db, candidate_id=candidate_id, actor=auth.actor_id, resolution="accepted", note=body.note)


@router.post("/candidates/{candidate_id}/reject", response_model=AICandidateRead)
def post_reject_ai_candidate(
    candidate_id: int,
    body: AICandidateResolveRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AICandidateRead:
    return _resolve(db, candidate_id=candidate_id, actor=auth.actor_id, resolution="rejected", note=body.note)


def _resolve(db: Session, *, candidate_id: int, actor: str, resolution: str, note: str | None) -> AICandidateRead:
    try:
        candidate = resolve_candidate(db, candidate_id=candidate_id, actor=actor, resolution=resolution, note=note)
    except NotImplementedError as exc:
        db.rollback()
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if candidate is None:
        raise HTTPException(status_code=404, detail="AI candidate not found")
    db.commit()
    db.refresh(candidate)
    return AICandidateRead.model_validate(candidate)
