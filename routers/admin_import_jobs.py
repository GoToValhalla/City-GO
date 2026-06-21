"""Admin: запуск, повтор, публикация import jobs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from schemas.admin import AdminActionRequest, AdminImportJobActionResponse
from services.admin_city_import_job_service import (
    cancel_import_job,
    queue_city_enrichment_job,
    queue_city_import_job,
    reset_import_job_to_queued,
)
from services.admin_city_import_tasks import import_queue_summary
from services.admin_city_publication_service import publish_city
from services.admin_extended_service import get_admin_import_job, list_admin_import_jobs

router = APIRouter(prefix="/admin", tags=["admin-import-jobs"])


@router.get("/import-jobs/queue")
def read_import_job_queue(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return import_queue_summary(db)


@router.post("/import-jobs/{city_id}/run", response_model=AdminImportJobActionResponse)
def start_import_job(
    city_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_run"):
        raise HTTPException(409, "Запуск недоступен для текущего статуса")
    try:
        queue_city_import_job(db, city_id=city_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="queued",
        message="Импорт поставлен в очередь. Его выполнит import-worker, backend не держит тяжелую фоновую задачу.",
    )


@router.post("/import-jobs/{city_id}/retry", response_model=AdminImportJobActionResponse)
def retry_import_job(
    city_id: int,
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


@router.post("/import-jobs/{city_id}/publish", response_model=AdminImportJobActionResponse)
def publish_imported_city(
    city_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    body = payload or AdminActionRequest()
    try:
        result = publish_city(db, city_id, actor=auth.actor_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Город не найден")
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="published",
        message=f"Город опубликован. На сайт вышло мест: {result.places_published}. Скрыто: {result.places_hidden}.",
    )


@router.post("/import-jobs/{city_id}/enrich", response_model=AdminImportJobActionResponse)
def enrich_city_job(
    city_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Город не найден")
    try:
        queue_city_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="queued",
        message="Обогащение поставлено в очередь: адреса → фото → категории → качество.",
    )


@router.post("/import-jobs/enrich-all", response_model=AdminImportJobActionResponse)
def enrich_all_cities_job(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminImportJobActionResponse:
    city_ids = [row.id for row in db.query(City.id).order_by(City.slug.asc()).all()]
    if not city_ids:
        raise HTTPException(404, "Города для обогащения не найдены")
    queued = 0
    skipped_running = 0
    for city_id in city_ids:
        try:
            queue_city_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
            queued += 1
        except ValueError:
            skipped_running += 1
    db.commit()
    return AdminImportJobActionResponse(
        city_id=0,
        status="queued",
        message=f"Обогащение городов поставлено в очередь: {queued}. Уже выполняются и пропущены: {skipped_running}.",
    )