"""LEGACY/SCOPE SCHEDULER SERVICE.

This service belongs to the old import-scope cron foundation around
`CityImportJob` and `CityImportScope`.

Active admin import source of truth:
- `services.admin_city_import_job_service`
- `services.admin_city_import_runner`
- `models.city_admin_import_job.CityAdminImportJob`

Rules:
- Do not use this service for admin import monitor/latest import status.
- Do not use it to change product publication state.
- Keep it only for old scope scheduler compatibility until the import storage
  consolidation task is done.
"""

from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models.city_import_job import CityImportJob
from models.city_import_scope import CityImportScope
from models.import_batch import ImportBatch


def due_scopes(db: Session, now: datetime) -> list[CityImportScope]:
    return db.query(CityImportScope).filter(
        CityImportScope.enabled.is_(True),
        CityImportScope.status.in_(("enabled", "needs_recheck")),
        CityImportScope.next_run_at <= now,
        CityImportScope.locked_at.is_(None),
    ).all()


def lock_scope(db: Session, scope: CityImportScope, now: datetime) -> bool:
    updated = db.query(CityImportScope).filter(
        and_(CityImportScope.id == scope.id, CityImportScope.locked_at.is_(None))
    ).update({"locked_at": now})
    db.commit()
    return updated == 1


def unlock_scope(db: Session, scope: CityImportScope) -> None:
    db.query(CityImportScope).filter(CityImportScope.id == scope.id).update({"locked_at": None})
    db.commit()


def create_batch(db: Session, scope: CityImportScope, mode: str = "dry_run") -> ImportBatch:
    batch = ImportBatch(city_id=scope.city_id, scope_id=scope.id, mode=mode, dry_run=mode != "apply")
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def finish_batch(db: Session, batch: ImportBatch, status: str, error_count: int = 0) -> ImportBatch:
    batch.status = status
    batch.errors_count = error_count
    batch.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch


def due_jobs(db: Session, now: datetime) -> list[CityImportJob]:
    return db.query(CityImportJob).filter(
        CityImportJob.status == "pending",
        CityImportJob.scheduled_for <= now,
    ).all()
