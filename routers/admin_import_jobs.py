"""Admin: запуск и повтор import jobs."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin import AdminImportJobActionResponse, AdminImportJobRead
from services.admin_city_import_job_service import cancel_import_job, ensure_import_job, reset_import_job_to_queued
from services.admin_city_import_tasks import run_enrichment_job_background, run_import_job_background
from services.admin_extended_service import get_admin_import_job

router = APIRouter(prefix="/admin", tags=["admin-import-jobs"])


@router.post("/import-jobs/{city_id}/run", response_model=AdminImportJobActionResponse)
def start_import_job(
    city_id: int,
    background_tasks: BackgroundTasks,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_run"):
        raise HTTPException(409, "Запуск недоступен для текущего статуса")
    ensure_import_job(db, city_id=city_id)
    db.commit()
    background_tasks.add_task(run_import_job_background, city_id, actor_id=auth.actor_id)
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="running",
        message="Импорт запущен в фоне. Обновите страницу через 1–2 минуты.",
    )


@router.post("/import-jobs/{city_id}/retry", response_model=AdminImportJobActionResponse)
def retry_import_job(
    city_id: int,
    background_tasks: BackgroundTasks,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_retry"):
        raise HTTPException(409, "Повтор недоступен для текущего статуса")
    try:
        reset_import_job_to_queued(db, city_id=city_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    background_tasks.add_task(run_import_job_background, city_id, actor_id=auth.actor_id)
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="queued",
        message="Повтор импорта поставлен в очередь.",
    )


@router.post("/import-jobs/{city_id}/cancel", response_model=AdminImportJobActionResponse)
def cancel_import_job_endpoint(
    city_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_cancel"):
        raise HTTPException(409, "Отмена недоступна для текущего статуса")
    try:
        cancel_import_job(db, city_id=city_id, actor_id=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="cancelled",
        message="Импорт отменён.",
    )


@router.post("/import-jobs/{city_id}/enrich", response_model=AdminImportJobActionResponse)
def enrich_city_job(
    city_id: int,
    background_tasks: BackgroundTasks,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Город не найден")
    ensure_import_job(db, city_id=city_id)
    db.commit()
    background_tasks.add_task(run_enrichment_job_background, city_id, actor_id=auth.actor_id)
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="running",
        message="Обогащение запущено: адреса → фото → категории → качество.",
    )
