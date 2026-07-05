"""Недавние запуски импорта и обогащения."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import CityEnrichmentRun
from schemas.data_pipeline_status import DataPipelineRecentRun
from services.data_pipeline_status.constants import RUN_STATUS_LABELS, RUN_TYPE_LABELS

RECENT_LIMIT = 12


def build_recent_runs(db: Session) -> list[DataPipelineRecentRun]:
    import_rows = (
        db.query(CityAdminImportJob)
        .order_by(CityAdminImportJob.created_at.desc(), CityAdminImportJob.id.desc())
        .limit(RECENT_LIMIT)
        .all()
    )
    enrichment_rows = (
        db.query(CityEnrichmentRun)
        .order_by(CityEnrichmentRun.created_at.desc(), CityEnrichmentRun.id.desc())
        .limit(RECENT_LIMIT)
        .all()
    )
    merged = [_from_import_job(db, row) for row in import_rows]
    merged.extend(_from_enrichment_run(db, row) for row in enrichment_rows)
    merged.sort(key=lambda row: row.started_at or row.finished_at or datetime.min, reverse=True)
    return merged[:RECENT_LIMIT]


def _from_import_job(db: Session, job: CityAdminImportJob) -> DataPipelineRecentRun:
    city = db.query(City).filter(City.id == job.city_id).first()
    return _run_payload(
        run_id=int(job.id),
        run_type=str(job.source or "admin_city_import"),
        city_slug=city.slug if city else None,
        city_name=city.name if city else None,
        status=str(job.status),
        started_at=job.started_at or job.created_at,
        finished_at=job.finished_at,
        error_summary=_trim(job.last_error),
    )


def _from_enrichment_run(db: Session, run: CityEnrichmentRun) -> DataPipelineRecentRun:
    city = db.query(City).filter(City.id == run.city_id).first() if run.city_id else None
    return _run_payload(
        run_id=int(run.id),
        run_type=str(run.run_type or "city_enrichment"),
        city_slug=city.slug if city else None,
        city_name=city.name if city else run.requested_city_name,
        status=str(run.status),
        started_at=run.started_at or run.created_at,
        finished_at=run.finished_at,
        error_summary=_trim(run.error_message),
    )


def _run_payload(
    *,
    run_id: int,
    run_type: str,
    city_slug: str | None,
    city_name: str | None,
    status: str,
    started_at: datetime | None,
    finished_at: datetime | None,
    error_summary: str | None,
) -> DataPipelineRecentRun:
    duration = None
    if started_at and finished_at:
        duration = max(0, int((finished_at - started_at).total_seconds()))
    return DataPipelineRecentRun(
        run_id=run_id,
        run_type=run_type,
        run_type_label=RUN_TYPE_LABELS.get(run_type, "Запуск конвейера"),
        city_slug=city_slug,
        city_name=city_name,
        status=status,
        status_label=RUN_STATUS_LABELS.get(status, "Неизвестно"),
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        error_summary=error_summary,
    )


def _trim(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text[:240] if text else None
