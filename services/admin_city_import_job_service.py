"""Очередь и выполнение admin city import jobs."""
from __future__ import annotations

import inspect
from datetime import datetime

from sqlalchemy.orm import Session

from data.scripts.backfill_missing_place_addresses import run as run_address_backfill
from data.scripts.enrich_place_images import run as run_image_enrich
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_job_payload import SNAPSHOT_KEY
from services.admin_city_import_log import log_import_event
from services.admin_import_job_change_service import CHANGE_TYPES, record_place_changes
from services.city_readiness.score import compute_city_readiness
from services.import_publication_finalize import finalize_import_publication
from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
from services.import_pipeline.runner import run_enrichment_pipeline
from services.import_pipeline.steps import STEP_CANCELLED, STEP_ERROR, STEP_QUEUED
from services.import_pipeline_foundation import run_foundation_pipeline
from services.photo_enrichment_diagnostics import attach_photo_diagnostics_to_summary, build_photo_enrichment_diagnostics
from services.place_auto_repair_service import PlaceAutoRepairService

class DuplicateActiveJobError(ValueError):
    """Raised when a queue action is attempted while a job is already
    queued/running for the city — prevents duplicate active jobs from
    repeated admin clicks (e.g. double-clicking "Добрать фото")."""

    def __init__(self, *, city_id: int, job_id: int, job_status: str, source: str):
        self.city_id = city_id
        self.job_id = job_id
        self.job_status = job_status
        self.source = source
        super().__init__("Pipeline уже выполняется")


SOURCE_FULL_IMPORT = "admin_city_import"
SOURCE_ENRICHMENT_ONLY = "admin_city_enrichment"
SOURCE_SNAPSHOT_REFRESH = "admin_snapshot_refresh"
SOURCE_ADDRESS_ENRICHMENT = "admin_address_enrichment"
SOURCE_PHOTO_ENRICHMENT = "admin_photo_enrichment"
ADDRESS_LIMIT = 5000
IMAGE_LIMIT = 2000
AUTO_REPAIR_CITY_SCAN_LIMIT = 1000

# Severity order (least to most severe) for combining the terminal status of
# independent pipeline stages (legacy collection/enrichment + foundation
# source-enrichment) into one truthful job status. A stage's status must
# never be silently widened back to "success" once any stage reported a
# worse outcome.
_STATUS_SEVERITY = {
    "success": 0,
    "success_with_warnings": 1,
    "partial_success": 2,
    "failed": 3,
}


def _combine_status(*statuses: str) -> str:
    """Return the most severe of the given terminal statuses.

    Unknown/blank statuses are treated as "success" so a stage that didn't
    report anything doesn't spuriously downgrade the combined result.
    """

    worst = "success"
    worst_rank = 0
    for status in statuses:
        rank = _STATUS_SEVERITY.get(status, 0)
        if rank > worst_rank:
            worst = status
            worst_rank = rank
    return worst


# --- Immutable lifecycle: explicit allowed-transition map -------------------
#
# queued -> running
# running -> success | success_with_warnings | partial_success | failed
# running -> stalled  (recovery marks a stuck row terminal; see
#                       mark_stalled_import_jobs in admin_city_import_tasks.py)
# queued  -> cancelled (an admin cancels before a worker ever claims it)
# running -> cancelled (an admin cancels a running job)
#
# Every other row->status transition is invalid and fails closed: no
# terminal status (success/success_with_warnings/partial_success/failed/
# cancelled/stalled) may ever transition to queued or running. A retry
# never mutates a terminal row's status — it inserts a brand-new row
# instead (see enqueue_or_retry_job below).
TERMINAL_STATUSES = frozenset({"success", "success_with_warnings", "partial_success", "failed", "cancelled", "stalled"})
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    # "failed" here covers a worker claiming a job and then crashing before
    # its own runner function reaches its first `running` transition (e.g.
    # an exception raised by _resolve_run_job itself) — the row is claimed
    # but never actually started, so it must still be terminable directly
    # from queued rather than getting stuck queued forever.
    "queued": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"success", "success_with_warnings", "partial_success", "failed", "stalled", "cancelled"}),
}


class InvalidJobTransitionError(ValueError):
    """Raised when code attempts to move a CityAdminImportJob row through a
    transition not present in _ALLOWED_TRANSITIONS — most importantly, any
    terminal -> queued/running transition, which is exactly the production
    Job #1 corruption (a finished row silently reset back to queued and
    reused by a later, unrelated worker run)."""

    def __init__(self, *, job_id: int, from_status: str, to_status: str):
        self.job_id = job_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"job #{job_id}: invalid transition {from_status} -> {to_status}")


def _transition(db: Session, job: CityAdminImportJob, new_status: str, *, actor_id: str | None = None) -> None:
    """The single place every status write on an existing row must go
    through. Fails closed (raises, does not silently coerce) on any
    transition not explicitly allowed, and records a diagnostic
    system_log event for the rejected attempt so an invalid transition is
    never silently swallowed."""
    old_status = str(job.status)
    if old_status == new_status:
        return
    allowed = _ALLOWED_TRANSITIONS.get(old_status, frozenset())
    if new_status not in allowed:
        log_import_event(
            db, event="import_job_invalid_transition", city_slug=None, actor_id=actor_id, level="error",
            message=f"Rejected invalid transition for job #{job.id}: {old_status} -> {new_status}",
            details={"job_id": job.id, "from_status": old_status, "to_status": new_status}, job_id=job.id,
        )
        raise InvalidJobTransitionError(job_id=job.id, from_status=old_status, to_status=new_status)
    job.status = new_status
    job.updated_at = datetime.utcnow()


def queue_city_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def queue_city_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    return queue_city_import_job(db, city_id=city_id, actor_id=actor_id)


def queue_city_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_SNAPSHOT_REFRESH, actor_id=actor_id)


def queue_city_address_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_ADDRESS_ENRICHMENT, actor_id=actor_id)


def queue_city_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_PHOTO_ENRICHMENT, actor_id=actor_id)


def load_job_for_run(db: Session, *, job_id: int, city_id: int) -> CityAdminImportJob:
    """The only way a runner (run_city_import_job, run_snapshot_refresh_job,
    etc.) may obtain the row it operates on. Requires the EXACT job_id the
    caller already claimed/created — never re-derives "the latest job for
    this city", which is exactly what let a runner started for one launch
    silently pick up a different, newer row created for the same city in
    the meantime. Raises if the row doesn't exist or belongs to a
    different city (defensive: callers must never mix up city_id/job_id)."""
    job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job is None:
        raise ValueError(f"Задача импорта #{job_id} не найдена")
    if int(job.city_id) != int(city_id):
        raise ValueError(f"Задача импорта #{job_id} принадлежит другому городу")
    return job


def _active_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id, CityAdminImportJob.status.in_(("queued", "running")))
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )


def _latest_terminal_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    from services.admin_city_import_job_payload import _latest_job
    job = _latest_job(db, city_id)
    if job is not None and job.status in TERMINAL_STATUSES:
        return job
    return None


def _preserved_snapshot_context(job: CityAdminImportJob | None, source: str) -> dict[str, object]:
    if job is None or source != SOURCE_SNAPSHOT_REFRESH:
        return {}
    previous = dict(job.step_details or {})
    preserved: dict[str, object] = {}
    photo_result = previous.get("latest_photo_enrichment") or previous.get("photo_enrichment")
    if isinstance(photo_result, dict):
        preserved["latest_photo_enrichment"] = photo_result
        preserved["photo_enrichment"] = photo_result
    address_result = previous.get("latest_address_enrichment") or previous.get("address_enrichment")
    if isinstance(address_result, dict):
        preserved["latest_address_enrichment"] = address_result
        preserved["address_enrichment"] = address_result
    auto_repair = previous.get("auto_repair")
    if isinstance(auto_repair, dict):
        preserved["auto_repair"] = auto_repair
    return preserved


def _enqueue_job(db: Session, *, city: City, source: str, actor_id: str | None) -> CityAdminImportJob:
    """Immutable enqueue (fix for CityAdminImportJob lifecycle invariant #1:
    one admin launch = one new row). Concurrency-safe idempotent winner
    selection: SELECT ... FOR UPDATE on the city's active row (if any)
    blocks a concurrent second enqueue until the first transaction commits
    or rolls back, so two near-simultaneous requests can never both insert
    an active row for the same city — the second sees the first's
    committed row and raises DuplicateActiveJobError with its real id,
    rather than racing to insert a second one. A terminal row for this
    city (any previous launch/retry) is NEVER reused or reset — a brand
    new row is always inserted, with previous_job_id pointing at the most
    recent terminal row so the retry chain is reconstructible without
    guessing."""
    active = (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city.id, CityAdminImportJob.status.in_(("queued", "running")))
        .with_for_update()
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )
    if active is not None:
        raise DuplicateActiveJobError(city_id=city.id, job_id=active.id, job_status=active.status, source=active.source)
    previous = _latest_terminal_job(db, city.id)
    scopes = db.query(CityImportScope).filter_by(city_id=city.id, enabled=True).count()
    preserved = _preserved_snapshot_context(previous, source)
    job = CityAdminImportJob(
        city_id=city.id,
        previous_job_id=previous.id if previous is not None else None,
        status="queued",
        source=source,
        scopes_total=scopes,
        current_step=STEP_QUEUED,
        step_details={"city_state_before_import": {"launch_status": city.launch_status, "is_active": bool(city.is_active)}, **preserved},
        retry_count=(int(previous.retry_count) + 1) if previous is not None else 0,
    )
    db.add(job)
    db.flush()
    log_import_event(
        db, event="import_job_created", city_slug=city.slug, actor_id=actor_id,
        message=f"Создана задача {source} #{job.id}" + (f" (повтор #{previous.id})" if previous is not None else ""),
        details={"job_id": job.id, "scopes_total": scopes, "source": source, "previous_job_id": previous.id if previous is not None else None},
        job_id=job.id,
    )
    return job


def _resolve_run_job(db: Session, *, city_id: int, job_id: int | None) -> CityAdminImportJob:
    """Resolve the exact row a run_*_job runner must operate on.

    job_id, when supplied (the worker path — run_queued_import_jobs
    already claimed this exact row under FOR UPDATE SKIP LOCKED), is the
    only source of truth: load_job_for_run rejects a mismatched city_id
    outright. Without job_id (the synchronous admin-router path, or a
    direct/CLI caller that never enqueued its own row), the city's current
    ACTIVE (queued/running) row is used if one exists — never "the latest
    row regardless of status", which could silently pick up an unrelated
    terminal row from a previous launch. If no active row exists either,
    one is created here via the normal immutable _enqueue_job path (the
    same convenience the old ensure_import_job provided for callers that
    invoke a runner directly without enqueuing first)."""
    if job_id is not None:
        return load_job_for_run(db, job_id=job_id, city_id=city_id)
    job = _active_job(db, city_id)
    if job is not None:
        return job
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError(f"Город #{city_id} не найден")
    return _enqueue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=None)


def retry_import_job(db: Session, *, city_id: int, actor_id: str | None = None) -> CityAdminImportJob:
    """Immutable retry (fix for lifecycle invariant #2: one retry = one new
    row with previous_job_id pointing at the prior row). Replaces the old
    reset_import_job_to_queued, which reused/reset the SAME row — the
    exact mechanism behind the production Job #1 corruption. Only valid
    when the city's latest job is itself terminal (not queued/running);
    _enqueue_job's own active-row lock already rejects a concurrent retry
    against a still-active job with the correct DuplicateActiveJobError."""
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    return _enqueue_job(db, city=city, source=SOURCE_FULL_IMPORT, actor_id=actor_id)


def run_city_import_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    if job.status == "running":
        raise ValueError("Импорт уже выполняется")
    if job.current_step == STEP_CANCELLED:
        raise ValueError("Задача отменена. Создайте новую через повтор.")
    _transition(db, job, "running", actor_id=actor_id)
    job.source = SOURCE_FULL_IMPORT
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    job.scopes_total = db.query(CityImportScope).filter_by(city_id=city_id, enabled=True).count()
    log_import_event(db, event="import_job_started", city_slug=city.slug, actor_id=actor_id, message=f"Старт полного pipeline #{job.id}", details={"job_id": job.id, "source": job.source}, job_id=job.id)
    db.commit()
    try:
        legacy = run_enrichment_pipeline(db, job=job, city=city, actor_id=actor_id, force=True, notify_completion=False)
        db.refresh(job)
        db.refresh(city)
        legacy_status = job.status
        ids = [int(v) for v in legacy.get("changed_place_ids", [])]
        warnings = list((job.step_details or {}).get("warnings") or [])
        saved = (job.places_found, job.places_saved, job.scopes_succeeded)
        # Not routed through _transition: run_enrichment_pipeline (the
        # "legacy" collection/enrichment phase) may itself have already
        # driven the row to a terminal legacy_status (captured above) as
        # its own phase result — that is not a genuine terminal handoff,
        # it is this same run_city_import_job execution moving on to its
        # next internal phase (_foundation). The row never left this
        # worker run/call stack, so this is not the cross-run reuse the
        # immutable-lifecycle fix targets.
        job.status = "running"
        job.finished_at = None
        db.commit()
        source = _foundation(db, city, job, actor_id, ids)
        source_status = job.status
        job.places_found, job.places_saved, job.scopes_succeeded = saved
        auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=ids)
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}
        places = db.query(Place).filter(Place.id.in_(ids)).order_by(Place.id).all() if ids else []
        record_place_changes(db, job=job, places=places, since=job.started_at or datetime.utcnow())
        if source_status in {"partial_success", "success_with_warnings", "failed"} or int(source.get("failed") or 0) > 0:
            warnings.append({"step": "source_enrichment", "error": f"Ошибок этапов обогащения: {int(source.get('failed') or 0)}"})
        if legacy_status in {"partial_success", "failed"}:
            warnings.append({"step": "collection_and_legacy_enrichment", "error": f"Статус этапа сбора/обогащения: {legacy_status}", "last_error": job.last_error})
        job.step_details = {**dict(job.step_details or {}), "warnings": warnings, "changed_place_ids": ids, "has_changes": bool(ids), "auto_repair": auto_repair, "unified_pipeline": {"collection_and_legacy_enrichment": legacy, "source_enrichment": source, "readiness_score": readiness.get("readiness_score"), "auto_repair": auto_repair, "completed": True}}
        combined_status = _combine_status(legacy_status, source_status, "success_with_warnings" if warnings else "success")
        publication = finalize_import_publication(
            db,
            city=city,
            job=job,
            place_ids=ids,
            import_status=combined_status,
        )
        if publication.get("status") == "failed" and combined_status in {"success", "success_with_warnings"}:
            combined_status = "partial_success"
            job.last_error = f"publication_stage_failed:{','.join(publication.get('reasons', []))}"
        _transition(db, job, combined_status, actor_id=actor_id)
        job.finished_at = datetime.utcnow()
        city.last_import_at = job.finished_at
        job.step_details = {
            **dict(job.step_details or {}),
            "publication_finalize": publication,
        }
        _refresh_snapshot_light(db, city=city, job=job, source="import_worker_finished")
        log_import_event(db, event="unified_import_pipeline_finished", city_slug=city.slug, actor_id=actor_id, message=f"Полный pipeline #{job.id}: {len(ids)} изменений; auto-repair {auto_repair.get('repaired_count', 0)}; публикация города сохранена", details={"job_id": job.id, "changed_places": len(ids), "warnings": warnings, "auto_repair": auto_repair, "city_launch_status": city.launch_status, "city_is_active": bool(city.is_active)}, job_id=job.id)
        db.commit()
        _alert(db, city, job, len(ids), readiness, warnings)
    except Exception as exc:
        db.rollback()
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job.id).first()
        city = db.query(City).filter(City.id == city_id).first()
        total = db.query(Place).filter(Place.city_id == city_id).count()
        ids = [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])] if job else []
        if job:
            # This run's own changed_place_ids (recorded before the crash) is the
            # only truthful signal that *this* run made meaningful progress.
            # total > 0 (city has any place, possibly from a prior run) must not
            # by itself downgrade a hard failure of this run to partial_success.
            try:
                _transition(db, job, "partial_success" if ids else "failed", actor_id=actor_id)
            except InvalidJobTransitionError:
                pass
            job.last_error = str(exc)[:2000]
            job.finished_at = datetime.utcnow()
        if city is not None:
            city.last_import_at = datetime.utcnow()
        if job and city is not None:
            _refresh_snapshot_light(db, city=city, job=job, source="import_pipeline_failed")
        db.commit()
        send_admin_alert(title="Import completed with warnings" if total > 0 else "Import pipeline failed", message=f"Pipeline прерван. Изменённых мест: {len(ids)}. Публикация города не изменялась.", level="warning" if total > 0 else "error", city_slug=city.slug if city else None, job_id=int(job.id) if job else None, details={"status": job.status if job else "failed", "places_total": total, "changed_places": len(ids), "city_launch_status": city.launch_status if city else None, "city_is_active": bool(city.is_active) if city else None, "warnings": [{"step": "unified_pipeline", "error": str(exc)[:1000]}]})
    db.refresh(job)
    return job


def run_snapshot_refresh_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    _transition(db, job, "running", actor_id=actor_id)
    job.source = SOURCE_SNAPSHOT_REFRESH
    job.current_step = "snapshot_refresh"
    job.started_at = datetime.utcnow()
    db.commit()
    _refresh_snapshot_light(db, city=city, job=job, source="snapshot_refresh_job")
    _transition(db, job, "success", actor_id=actor_id)
    job.finished_at = datetime.utcnow()
    job.current_step = "snapshot_ready"
    db.commit()
    db.refresh(job)
    return job


def _enrichment_prerequisites(db: Session, *, city: City) -> dict[str, object]:
    """Shared prerequisite check for standalone admin enrichment actions
    (Добрать фото / Добрать адреса). These do not go through run_enrichment_pipeline,
    so unlike the main import they had no check that collecting_places ever
    produced usable places before scanning — this made "eligible but never run"
    indistinguishable from "ran and found nothing to do"."""
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    blocked_reason = None if places_total > 0 else "no_places_in_city"
    return {
        "places_total": places_total,
        "blocked_reason": blocked_reason,
        "ok": blocked_reason is None,
    }


def run_address_enrichment_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    _transition(db, job, "running", actor_id=actor_id)
    job.source = SOURCE_ADDRESS_ENRICHMENT
    job.current_step = "finding_addresses"
    job.started_at = datetime.utcnow()
    db.commit()
    prerequisites = _enrichment_prerequisites(db, city=city)
    if not prerequisites["ok"]:
        job.step_details = {
            **dict(job.step_details or {}),
            "address_enrichment": {"scanned_places": 0, "updated": 0, "checked": 0, "blocked_reason": prerequisites["blocked_reason"]},
            "prerequisites": prerequisites,
        }
        _transition(db, job, "failed", actor_id=actor_id)
        job.finished_at = datetime.utcnow()
        job.current_step = STEP_ERROR
        job.last_error = f"Добор адресов заблокирован: {prerequisites['blocked_reason']}"
        log_import_event(db, event="address_enrichment_blocked", city_slug=city.slug, actor_id=actor_id, level="warning", message=f"Добор адресов #{job.id} заблокирован: {prerequisites['blocked_reason']}", details={"job_id": job.id, "city_id": city.id, "source": SOURCE_ADDRESS_ENRICHMENT, "prerequisites": prerequisites}, job_id=job.id)
        db.commit()
        db.refresh(job)
        return job
    result = run_address_backfill(["--city", city.slug, "--limit", str(ADDRESS_LIMIT), "--apply"])
    auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=[])
    job.step_details = {**dict(job.step_details or {}), "address_enrichment": result, "auto_repair": auto_repair, "prerequisites": prerequisites}
    deadline_exceeded = bool(isinstance(result, dict) and result.get("deadline_exceeded"))
    errors = int(result.get("errors") or 0) if isinstance(result, dict) else 0
    _transition(db, job, "success_with_warnings" if deadline_exceeded or errors > 0 else "success", actor_id=actor_id)
    if deadline_exceeded:
        checked = int(result.get("checked") or 0) if isinstance(result, dict) else 0
        job.last_error = f"Добор адресов остановлен по таймауту выполнения после проверки {checked} мест."
    job.finished_at = datetime.utcnow()
    job.current_step = "snapshot_refresh"
    db.commit()
    _refresh_snapshot_light(db, city=city, job=job, source="address_enrichment_finished")
    db.refresh(job)
    return job


def run_photo_enrichment_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    _transition(db, job, "running", actor_id=actor_id)
    job.source = SOURCE_PHOTO_ENRICHMENT
    job.current_step = "finding_images"
    job.started_at = datetime.utcnow()
    db.commit()
    prerequisites = _enrichment_prerequisites(db, city=city)
    if not prerequisites["ok"]:
        photo_diagnostics = build_photo_enrichment_diagnostics(db, city, enrichment_result=None, step_status="blocked", scan_limit=IMAGE_LIMIT)
        job.step_details = {
            **dict(job.step_details or {}),
            "photo_enrichment": {"scanned_places": 0, "created": 0, "candidates_found": 0, "blocked_reason": prerequisites["blocked_reason"]},
            "photo_diagnostics": photo_diagnostics,
            "prerequisites": prerequisites,
        }
        _transition(db, job, "failed", actor_id=actor_id)
        job.finished_at = datetime.utcnow()
        job.current_step = STEP_ERROR
        job.last_error = f"Добор фото заблокирован: {prerequisites['blocked_reason']}"
        log_import_event(db, event="photo_enrichment_blocked", city_slug=city.slug, actor_id=actor_id, level="warning", message=f"Добор фото #{job.id} заблокирован: {prerequisites['blocked_reason']}", details={"job_id": job.id, "city_id": city.id, "source": SOURCE_PHOTO_ENRICHMENT, "prerequisites": prerequisites}, job_id=job.id)
        db.commit()
        db.refresh(job)
        return job
    result = run_image_enrich(["--city", city.slug, "--limit", str(IMAGE_LIMIT), "--apply"])
    if isinstance(result, dict) and "photo_diagnostics" not in result:
        result = attach_photo_diagnostics_to_summary(db, city, result, scan_limit=IMAGE_LIMIT)
    scanned = int(result.get("scanned_places") or 0) if isinstance(result, dict) else 0
    created = int(result.get("created") or 0) if isinstance(result, dict) else 0
    errors = result.get("errors") if isinstance(result, dict) else []
    provider_status = result.get("provider_status") if isinstance(result, dict) else None
    photo_diagnostics = result.get("photo_diagnostics") if isinstance(result, dict) else build_photo_enrichment_diagnostics(db, city, enrichment_result=result if isinstance(result, dict) else None, scan_limit=IMAGE_LIMIT)
    auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=[])
    job.places_found = scanned
    job.places_saved = created
    job.total_items = scanned
    job.processed_items = scanned
    job.successful_items = scanned
    job.failed_items = len(errors or []) if isinstance(errors, list) else 0
    job.step_details = {**dict(job.step_details or {}), "photo_enrichment": result, "photo_diagnostics": photo_diagnostics, "auto_repair": auto_repair, "prerequisites": prerequisites}
    _transition(db, job, "success_with_warnings" if created <= 0 and str(photo_diagnostics.get("provider_status") or "") not in {"success", ""} else "success", actor_id=actor_id)
    if isinstance(result, dict) and result.get("deadline_exceeded"):
        job.last_error = f"Добор фото остановлен по таймауту выполнения после просмотра {scanned} мест."
    job.finished_at = datetime.utcnow()
    job.current_step = "snapshot_refresh"
    log_import_event(db, event="photo_enrichment_finished", city_slug=city.slug, actor_id=actor_id, message=f"Добор фото #{job.id}: создано {created}, просмотрено {scanned}, provider={provider_status or 'unknown'}", details={"job_id": job.id, "source": SOURCE_PHOTO_ENRICHMENT, "photo_enrichment": result, "photo_diagnostics": photo_diagnostics, "auto_repair": auto_repair}, job_id=job.id)
    db.commit()
    _refresh_snapshot_light(db, city=city, job=job, source="photo_enrichment_finished")
    db.refresh(job)
    return job


def _refresh_snapshot_light(db: Session, *, city: City, job: CityAdminImportJob, source: str) -> dict[str, object]:
    total = db.query(Place).filter(Place.city_id == city.id).count()
    published = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
    without_address = db.query(Place).filter(Place.city_id == city.id, Place.address.is_(None)).count()
    without_photo = db.query(Place).filter(Place.city_id == city.id, Place.image_url.is_(None)).count()
    without_description = db.query(Place).filter(Place.city_id == city.id, Place.short_description.is_(None)).count()
    pending_photos = db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    def pct(missing: int) -> float:
        return round(((total - missing) / total) * 100, 1) if total else 0.0
    coverage = {"places_total": int(total), "places_published": int(published), "places_unpublished": max(int(total) - int(published), 0), "without_address": int(without_address), "without_photo": int(without_photo), "without_description": int(without_description), "address_coverage_pct": pct(int(without_address)), "photo_coverage_pct": pct(int(without_photo)), "description_coverage_pct": pct(int(without_description)), "pending_photos": int(pending_photos)}
    existing_changes = dict(job.step_details or {}).get("change_summary")
    changes = existing_changes if isinstance(existing_changes, dict) else {"job_id": job.id, "city_id": city.id, "city_slug": city.slug, **{key: 0 for key in CHANGE_TYPES}}
    changes = {**changes, "total_changes": sum(int(changes.get(key) or 0) for key in CHANGE_TYPES)}
    auto_repair = dict(job.step_details or {}).get("auto_repair")
    snapshot = {"version": 1, "source": source, "taken_at": datetime.utcnow().isoformat(), "city_id": city.id, "city_slug": city.slug, "job_id": job.id, "data_coverage": coverage, "change_summary": changes, "auto_repair": auto_repair if isinstance(auto_repair, dict) else None}
    details = dict(job.step_details or {})
    details[SNAPSHOT_KEY] = snapshot
    details["data_coverage"] = coverage
    details["change_summary"] = changes
    job.step_details = details
    job.updated_at = datetime.utcnow()
    db.commit()
    return snapshot


def _run_auto_repair(db: Session, *, city: City, job: CityAdminImportJob, changed_place_ids: list[int]) -> dict[str, object]:
    query = db.query(Place).filter(Place.city_id == city.id)
    if changed_place_ids:
        query = query.filter(Place.id.in_(changed_place_ids))
    else:
        query = query.order_by(Place.id.desc()).limit(AUTO_REPAIR_CITY_SCAN_LIMIT)
    places = query.all()
    summary = PlaceAutoRepairService().repair_places(places)
    payload = _serialize_auto_repair_summary(summary)
    details = dict(job.step_details or {})
    details["auto_repair"] = payload
    job.step_details = details
    log_import_event(db, event="place_auto_repair_finished", city_slug=city.slug, actor_id=None, message=f"Auto-repair #{job.id}: repaired={summary.repaired_count}, review={summary.needs_review_count}, skipped={summary.skipped_count}", details={"job_id": job.id, "auto_repair": payload}, job_id=job.id)
    return payload


def _serialize_auto_repair_summary(summary: PlaceAutoRepairSummary) -> dict[str, object]:
    return {"repaired_count": int(summary.repaired_count), "needs_review_count": int(summary.needs_review_count), "skipped_count": int(summary.skipped_count), "by_reason": dict(summary.by_reason), "by_category": dict(summary.by_category), "items": [item.__dict__ for item in summary.items[:200]]}


def _foundation(db, city, job, actor_id, ids):
    kwargs = {"db": db, "city": city, "job": job, "actor": actor_id}
    if "place_ids" in inspect.signature(run_foundation_pipeline).parameters:
        kwargs["place_ids"] = ids
    return run_foundation_pipeline(**kwargs)


def _alert(db, city, job, changed, readiness, warnings):
    total = db.query(Place).filter(Place.city_id == city.id).count()
    auto_repair = dict(job.step_details or {}).get("auto_repair")
    send_admin_alert(title="Import completed with warnings" if warnings else "Import pipeline finished", message=f"{city.name}: {changed} мест обновлено. Публикация города сохранена." if changed else f"{city.name}: изменений нет, публикация сохранена.", level="warning" if warnings else "info", city_slug=city.slug, job_id=int(job.id), details={"status": job.status, "source": job.source, "places_total": total, "changed_places": changed, "city_launch_status": city.launch_status, "city_is_active": bool(city.is_active), "readiness": readiness, "auto_repair": auto_repair if isinstance(auto_repair, dict) else None, "warnings": warnings})


def run_enrichment_only_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    if job.status == "running":
        raise ValueError("Pipeline уже выполняется")
    _transition(db, job, "running", actor_id=actor_id)
    job.source = SOURCE_ENRICHMENT_ONLY
    job.started_at = datetime.utcnow()
    job.finished_at = None
    job.last_error = None
    db.commit()
    try:
        run_enrichment_only_pipeline(db, job=job, city=city, actor_id=actor_id)
        db.refresh(job)
        enrichment_only_status = job.status
        ids = [int(v) for v in ((job.step_details or {}).get("changed_place_ids") or [])]
        _foundation(db, city, job, actor_id, ids)
        source_status = job.status
        auto_repair = _run_auto_repair(db, city=city, job=job, changed_place_ids=ids)
        job.step_details = {**dict(job.step_details or {}), "auto_repair": auto_repair}
        _transition(db, job, _combine_status(enrichment_only_status, source_status, "success"), actor_id=actor_id)
        job.finished_at = datetime.utcnow()
        _refresh_snapshot_light(db, city=city, job=job, source="enrichment_only_finished")
    except Exception as exc:
        try:
            _transition(db, job, "failed", actor_id=actor_id)
        except InvalidJobTransitionError:
            pass
        job.current_step = STEP_ERROR
        job.last_error = str(exc)[:2000]
        job.failed_items = max(int(job.failed_items or 0), 1)
        job.finished_at = datetime.utcnow()
        job.updated_at = job.finished_at
        details = dict(job.step_details or {})
        details["worker_exception"] = {"error": str(exc)[:1000], "failed_at": job.finished_at.isoformat()}
        job.step_details = details
        db.commit()
        raise
    db.refresh(job)
    return job


def cancel_import_job(db: Session, *, city_id: int, actor_id: str, job_id: int | None = None) -> CityAdminImportJob:
    job = _resolve_run_job(db, city_id=city_id, job_id=job_id)
    if job.status != "running" and job.current_step not in {STEP_QUEUED, "queued"} and job.status in {"success", "failed"}:
        raise ValueError("Задача уже завершена")
    _transition(db, job, "cancelled", actor_id=actor_id)
    job.current_step = STEP_CANCELLED
    job.cancelled_at = datetime.utcnow()
    job.finished_at = datetime.utcnow()
    city = db.query(City).filter(City.id == city_id).first()
    if city:
        log_import_event(db, event="import_job_cancelled", city_slug=city.slug, actor_id=actor_id, message=f"Импорт #{job.id} отменён без изменения публикации города", details={"job_id": job.id, "source": job.source}, job_id=job.id)
    db.commit()
    db.refresh(job)
    return job
