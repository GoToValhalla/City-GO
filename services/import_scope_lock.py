"""Scope lock ownership for OSM import cron targets."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.import_job_service import lock_scope, unlock_scope
from services.import_pipeline.steps import STALL_THRESHOLD_MINUTES

_ACTIVE_JOB_STATUSES = ("queued", "running")


def scope_lock_key(scope: CityImportScope) -> str:
    return f"city:{scope.city_id}:scope:{scope.code}"


def active_city_admin_import_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(
            CityAdminImportJob.city_id == city_id,
            CityAdminImportJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        .order_by(CityAdminImportJob.updated_at.desc(), CityAdminImportJob.id.desc())
        .first()
    )


def _is_stale_lock(scope: CityImportScope, now: datetime) -> bool:
    if scope.locked_at is None:
        return False
    age = max(0.0, (now - scope.locked_at).total_seconds())
    return age > timedelta(minutes=STALL_THRESHOLD_MINUTES).total_seconds()


def _should_reclaim_lock(
    *,
    scope: CityImportScope,
    now: datetime,
    force: bool,
    city_admin_import_job_id: int | None,
    active_job: CityAdminImportJob | None,
) -> bool:
    if scope.locked_at is None:
        return False
    if _is_stale_lock(scope, now):
        return True
    if city_admin_import_job_id is not None and active_job is not None and int(active_job.id) == int(city_admin_import_job_id):
        return True
    if force and active_job is None:
        return True
    return False


def acquire_scope_lock(
    db: Session,
    scope: CityImportScope,
    now: datetime,
    *,
    force: bool = False,
    city_admin_import_job_id: int | None = None,
) -> dict[str, object]:
    lock_key = scope_lock_key(scope)
    active_job = active_city_admin_import_job(db, scope.city_id)
    owner_job_id = int(active_job.id) if active_job is not None else None
    current_job_id = int(city_admin_import_job_id) if city_admin_import_job_id is not None else None
    stale = _is_stale_lock(scope, now)

    if scope.locked_at is not None and _should_reclaim_lock(
        scope=scope,
        now=now,
        force=force,
        city_admin_import_job_id=city_admin_import_job_id,
        active_job=active_job,
    ):
        unlock_scope(db, scope)
        db.refresh(scope)
        stale = False

    if scope.locked_at is None and lock_scope(db, scope, now):
        return {
            "acquired": True,
            "lock_key": lock_key,
            "owner_job_id": current_job_id,
            "current_job_id": current_job_id,
            "stale": False,
            "retryable": False,
        }

    if scope.locked_at is not None:
        return {
            "acquired": False,
            "lock_key": lock_key,
            "owner_job_id": owner_job_id,
            "current_job_id": current_job_id,
            "stale": stale,
            "retryable": True,
            "admin_hint": "Scope уже заблокирован другим import job. Дождитесь завершения или повторите позже.",
        }

    return {
        "acquired": False,
        "lock_key": lock_key,
        "owner_job_id": owner_job_id,
        "current_job_id": current_job_id,
        "stale": stale,
        "retryable": True,
        "admin_hint": "Не удалось захватить scope lock. Повторите сбор города.",
    }
