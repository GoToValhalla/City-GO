"""Финализация admin city import job."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_log import log_import_event


def _apply_summary(
    db: Session,
    *,
    job: CityAdminImportJob,
    city: City,
    summary: dict[str, Any],
    actor_id: str,
) -> None:
    job.scopes_succeeded = int(summary.get("scopes_succeeded") or 0)
    job.places_found = int(summary.get("places_found") or 0)
    job.places_saved = int(summary.get("places_saved") or 0)
    job.finished_at = datetime.utcnow()
    places_total = db.query(Place).filter(Place.city_id == city.id).count()
    status = str(summary.get("status") or "failed")
    if status == "success" and places_total == 0 and job.scopes_succeeded == 0:
        status = "failed"
        job.last_error = summary.get("last_error") or "Нет scopes для импорта"
    elif status == "failed":
        job.last_error = str(summary.get("last_error") or "Импорт завершился с ошибкой")
    job.status = status
    city.launch_status = "imported" if status == "success" else "import_failed"
    event = "import_job_finished" if status == "success" else "import_job_failed"
    log_import_event(
        db, event=event, city_slug=city.slug, actor_id=actor_id,
        level="info" if status == "success" else "error",
        message=f"Импорт #{job.id}: {status}, мест в городе {places_total}",
        details={"job_id": job.id, "places_total": places_total, **summary},
    )


def _fail_job(db: Session, *, job: CityAdminImportJob, city: City, actor_id: str, error: str) -> None:
    job.status = "failed"
    job.last_error = error[:2000]
    job.finished_at = datetime.utcnow()
    city.launch_status = "import_failed"
    log_import_event(db, event="import_job_failed", city_slug=city.slug, actor_id=actor_id, level="error",
                     message=f"Импорт #{job.id} упал: {error}", details={"job_id": job.id})
