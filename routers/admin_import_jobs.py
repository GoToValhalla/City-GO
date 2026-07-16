"""Admin: запуск, повтор и публикация единых import jobs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from schemas.admin import (
    AdminActionRequest,
    AdminCityPublicationPreviewResponse,
    AdminCityPublishRequest,
    AdminImportJobActionResponse,
    AdminImportJobChangeListResponse,
    AdminImportJobChangeRead,
    AdminImportJobChangeSummaryResponse,
    AdminImportJobListResponse,
    AdminImportJobRead,
)
from schemas.admin_import_job_diagnostic import ImportJobDiagnostic
from services.admin_city_import_job_payload import refresh_import_job_snapshot
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic
from services.admin_city_import_job_service import (
    DuplicateActiveJobError,
    cancel_import_job,
    queue_city_address_enrichment_job,
    queue_city_enrichment_job,
    queue_city_import_job,
    queue_city_photo_enrichment_job,
    queue_city_snapshot_refresh_job,
    retry_import_job as retry_import_job_service,
)
from services.admin_city_import_tasks import import_queue_summary
from services.admin_city_publication_service import preview_city_publication, publish_city
from services.admin_extended_service import get_admin_import_job
from services.admin_import_job_change_service import CHANGE_TYPES, import_job_changes_summary, list_import_job_changes, serialize_change
from services.admin_import_jobs_fast import list_admin_import_jobs_fast

router = APIRouter(prefix="/admin", tags=["admin-import-jobs"])


def _duplicate_job_conflict(exc: DuplicateActiveJobError) -> HTTPException:
    """A repeated click while a job is already queued/running must return
    explicit job_id/status/reason, not just a bare message — so the admin UI
    can tell the caller which existing job is already in flight."""
    return HTTPException(
        status_code=409,
        detail={
            "result": "blocked",
            "reason": "duplicate_active_job",
            "message": str(exc),
            "job_id": exc.job_id,
            "job_status": exc.job_status,
            "source": exc.source,
        },
    )


@router.get("/import-jobs", response_model=AdminImportJobListResponse)
def read_import_jobs(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobListResponse:
    payload = list_admin_import_jobs_fast(db, limit=limit, offset=offset)
    return AdminImportJobListResponse(items=[AdminImportJobRead.model_validate(item) for item in payload["items"]], total=int(payload["total"]), limit=int(payload["limit"]), offset=int(payload["offset"]))


@router.get("/import-jobs/queue")
def read_import_job_queue(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    return import_queue_summary(db)


@router.get("/import-jobs/{city_id}", response_model=AdminImportJobRead)
def read_import_job(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobRead:
    payload = get_admin_import_job(db, city_id)
    if payload is None:
        raise HTTPException(404, "Задача импорта не найдена")
    return AdminImportJobRead.model_validate(payload)


@router.get("/import-jobs/{job_id}/diagnostic", response_model=ImportJobDiagnostic)
def read_import_job_diagnostic(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ImportJobDiagnostic:
    payload = build_import_job_diagnostic(db, job_id=job_id)
    if payload is None:
        raise HTTPException(404, "Задача импорта не найдена")
    return ImportJobDiagnostic.model_validate(payload)


@router.get("/import-jobs/{city_id}/changes", response_model=AdminImportJobChangeListResponse)
def read_import_job_changes(city_id: int, change_type: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobChangeListResponse:
    if change_type is not None and change_type not in CHANGE_TYPES:
        raise HTTPException(400, "Неверный тип изменения")
    if get_admin_import_job(db, city_id) is None:
        raise HTTPException(404, "Задача импорта не найдена")
    rows, total = list_import_job_changes(db, city_id=city_id, change_type=change_type, limit=limit, offset=offset)
    return AdminImportJobChangeListResponse(items=[AdminImportJobChangeRead.model_validate(serialize_change(row)) for row in rows], total=total, limit=limit, offset=offset)


@router.get("/import-jobs/{city_id}/changes/summary", response_model=AdminImportJobChangeSummaryResponse)
def read_import_job_changes_summary(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobChangeSummaryResponse:
    payload = import_job_changes_summary(db, city_id=city_id)
    if payload is None:
        raise HTTPException(404, "Задача импорта не найдена")
    return AdminImportJobChangeSummaryResponse.model_validate(payload)


@router.post("/import-jobs/{city_id}/snapshot/refresh", response_model=AdminImportJobActionResponse)
def refresh_import_snapshot_endpoint(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    try:
        queue_city_snapshot_refresh_job(db, city_id=city_id, actor_id=auth.actor_id)
        db.commit()
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Обновление snapshot поставлено в очередь.")


@router.post("/import-jobs/{city_id}/snapshot/refresh-now", response_model=AdminImportJobActionResponse)
def refresh_import_snapshot_now_endpoint(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise HTTPException(404, "Город не найден")
    snapshot = refresh_import_job_snapshot(db, city_id=city_id, source="admin_manual_refresh_now")
    coverage = snapshot.get("data_coverage") if isinstance(snapshot.get("data_coverage"), dict) else {}
    places_count = int(coverage.get("places_total") or 0)
    return AdminImportJobActionResponse(
        city_id=city_id,
        status="success",
        message=f"Snapshot обновлён. Мест в городе: {places_count}.",
        snapshot_source=str(snapshot.get("source") or "admin_manual_refresh_now"),
        places_count=places_count,
        reason=None,
    )


@router.post("/import-jobs/{city_id}/enrich-addresses", response_model=AdminImportJobActionResponse)
def enrich_addresses(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    try:
        queue_city_address_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
        db.commit()
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Добор адресов поставлен в очередь.")


@router.post("/import-jobs/{city_id}/enrich-photos", response_model=AdminImportJobActionResponse)
def enrich_photos(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    try:
        queue_city_photo_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
        db.commit()
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Добор фото поставлен в очередь.")


@router.post("/import-jobs/{city_id}/run", response_model=AdminImportJobActionResponse)
def start_import_job(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_run"):
        if item.get("can_retry"):
            try:
                retry_import_job_service(db, city_id=city_id, actor_id=auth.actor_id)
            except DuplicateActiveJobError as exc:
                raise _duplicate_job_conflict(exc) from exc
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            db.commit()
            return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Текущий запуск уже был reviewable/failed. Вместо /run автоматически выполнен /retry.")
        raise HTTPException(409, "Запуск недоступен для текущего статуса")
    try:
        queue_city_import_job(db, city_id=city_id, actor_id=auth.actor_id)
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Полный сбор и обогащение поставлены в очередь.")


@router.post("/import-jobs/{city_id}/retry", response_model=AdminImportJobActionResponse)
def retry_import_job(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_retry"):
        raise HTTPException(409, "Повтор недоступен для текущего статуса")
    try:
        retry_import_job_service(db, city_id=city_id, actor_id=auth.actor_id)
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.commit()
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Повтор полного сбора и обогащения поставлен в очередь.")


@router.post("/import-jobs/{city_id}/cancel", response_model=AdminImportJobActionResponse)
def cancel_import_job_endpoint(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Задача импорта не найдена")
    if not item.get("can_cancel"):
        raise HTTPException(409, "Отмена недоступна для текущего статуса")
    try:
        cancel_import_job(db, city_id=city_id, actor_id=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return AdminImportJobActionResponse(city_id=city_id, status="cancelled", message="Сбор и обогащение отменены.")


@router.get("/import-jobs/{city_id}/publish-preview", response_model=AdminCityPublicationPreviewResponse)
def preview_city_publish(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminCityPublicationPreviewResponse:
    """Read-only dry-run using the exact same gate/eligibility publish_city
    itself applies below — see services/place_publication_eligibility.py."""
    preview = preview_city_publication(db, city_id)
    if preview is None:
        raise HTTPException(404, "Город не найден")
    return AdminCityPublicationPreviewResponse(
        city_id=preview.city_id,
        gate_allowed=preview.gate_allowed,
        gate_reasons=list(preview.gate_reasons),
        places_total=preview.places_total,
        would_publish_place_ids=list(preview.would_publish_place_ids),
        would_hide_place_ids=list(preview.would_hide_place_ids),
        hide_reasons_by_place_id={pid: list(reasons) for pid, reasons in preview.hide_reasons_by_place_id.items()},
    )


@router.post("/import-jobs/{city_id}/publish", response_model=AdminImportJobActionResponse)
def publish_imported_city(city_id: int, payload: AdminCityPublishRequest | None = None, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    # override_readiness_gate is intentionally NOT part of AdminCityPublishRequest
    # (or any public request schema): until a separate authorization model exists,
    # no normal admin API/UI request may bypass the readiness gate. The parameter
    # on publish_city() itself remains service-only, for tests/internal emergency
    # use via direct Python calls — this endpoint always calls it with the
    # (unpassed, defaulting-False) gate enforced.
    body = payload or AdminCityPublishRequest()
    try:
        result = publish_city(db, city_id, actor=auth.actor_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "Город не найден")
    refresh_import_job_snapshot(db, city_id=city_id, source="city_published")
    return AdminImportJobActionResponse(city_id=city_id, status="published", message=f"Город опубликован. На сайт вышло мест: {result.places_published}. Скрыто: {result.places_hidden}.")


@router.post("/import-jobs/{city_id}/enrich", response_model=AdminImportJobActionResponse)
def enrich_city_job(city_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    item = get_admin_import_job(db, city_id)
    if item is None:
        raise HTTPException(404, "Город не найден")
    try:
        queue_city_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
    except DuplicateActiveJobError as exc:
        raise _duplicate_job_conflict(exc) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return AdminImportJobActionResponse(city_id=city_id, status="queued", message="Полный сбор и обогащение поставлен в очередь.")


@router.post("/import-jobs/enrich-all", response_model=AdminImportJobActionResponse)
def enrich_all_cities_job(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminImportJobActionResponse:
    city_ids = [row.id for row in db.query(City.id).order_by(City.slug.asc()).all()]
    if not city_ids:
        raise HTTPException(404, "Города для запуска не найдены")
    queued = 0
    skipped_running = 0
    for city_id in city_ids:
        try:
            queue_city_enrichment_job(db, city_id=city_id, actor_id=auth.actor_id)
            queued += 1
        except ValueError:
            skipped_running += 1
    db.commit()
    return AdminImportJobActionResponse(city_id=0, status="queued", message=f"Полный сбор и обогащение поставлен в очередь для городов: {queued}. Уже выполняются: {skipped_running}.")
