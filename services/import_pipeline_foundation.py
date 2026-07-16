"""Stage 1 automated import/enrichment foundation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.import_batch import ImportBatch
from models.place import Place
from services.import_job_step_service import record_step
from services.import_pipeline_foundation_steps import run_step

FOUNDATION_STEPS = (
    "collect_places",
    "normalize_categories",
    "backfill_addresses",
    "enrich_external_sources",
    "generate_ai_descriptions",
    "fetch_photo_candidates",
    "calculate_field_confidence",
    "apply_publication_decisions",
)
NON_CRITICAL_STEPS = {"enrich_external_sources", "generate_ai_descriptions", "fetch_photo_candidates"}


def run_foundation_pipeline(
    db: Session,
    *,
    city: City,
    job: CityAdminImportJob,
    actor: str,
    place_ids: list[int] | None = None,
) -> dict[str, int]:
    counters = _empty_counters()
    batch = _batch(db, city)
    query = db.query(Place).filter(Place.city_id == city.id)
    if place_ids is not None:
        query = query.filter(Place.id.in_(place_ids)) if place_ids else query.filter(False)
    places = query.order_by(Place.id.asc()).all()
    counters["found"] = len(places)
    manual_review_required = place_ids is not None

    if not places:
        _finish_batch(batch, counters, status="success", manual_review_required=manual_review_required)
        _write_job_counters(job, counters, phase_status="success")
        db.commit()
        return counters

    # phase_status is this function's own outcome, tracked as a local
    # variable rather than written onto job.status mid-loop — job.status
    # is the PARENT job's single terminal-status slot and must not be
    # mutated by an internal sub-phase (see run_city_import_job, which
    # combines this phase's outcome with others into exactly one final
    # _transition at the very end).
    phase_status = "success"
    for step in FOUNDATION_STEPS:
        record_step(db, job_id=job.id, step_name=step, status="started")
        try:
            run_step(db, step=step, city=city, job=job, batch=batch, places=places, counters=counters)
            record_step(db, job_id=job.id, step_name=step, status="success", counters=dict(counters))
        except Exception as exc:
            counters["failed"] += 1
            record_step(
                db,
                job_id=job.id,
                step_name=step,
                status="failed",
                counters=dict(counters),
                error_message=str(exc),
            )
            if step not in NON_CRITICAL_STEPS:
                _finish_batch(batch, counters, status="failed", manual_review_required=manual_review_required)
                _write_job_counters(job, counters, phase_status="failed")
                job.last_error = str(exc)[:2000]
                db.commit()
                raise
            phase_status = "partial_success"
    _finish_batch(
        batch,
        counters,
        status="partial_success" if phase_status == "partial_success" else "success",
        manual_review_required=manual_review_required,
    )
    _write_job_counters(job, counters, phase_status=phase_status)
    db.commit()
    return counters


def _batch(db: Session, city: City) -> ImportBatch:
    batch = ImportBatch(city_id=city.id, mode="pipeline", dry_run=False, status="running")
    db.add(batch)
    db.flush()
    return batch


def _finish_batch(
    batch: ImportBatch,
    counters: dict[str, int],
    *,
    status: str,
    manual_review_required: bool,
) -> None:
    batch.status = status
    batch.finished_at = datetime.utcnow()
    batch.raw_count = counters["found"]
    batch.normalized_count = counters["found"]
    batch.published_count = counters["auto_published"] + counters["limited_published"]
    batch.needs_review_count = counters["review_required"]
    batch.rejected_count = counters["rejected"]
    batch.errors_count = counters["failed"]
    batch.diff_summary = {
        "pipeline_counters": dict(counters),
        "publication_mode": "manual_review_required" if manual_review_required else "quality_gate",
    }


def _empty_counters() -> dict[str, int]:
    return {
        "found": 0,
        "enriched": 0,
        "auto_published": 0,
        "limited_published": 0,
        "review_required": 0,
        "rejected": 0,
        "failed": 0,
        "source_observations": 0,
        "fields_enriched": 0,
        "source_conflicts": 0,
        "provider_errors": 0,
    }


def _write_job_counters(job: CityAdminImportJob, counters: dict[str, int], *, phase_status: str) -> None:
    """Records this phase's own outcome in step_details (never job.status —
    see run_foundation_pipeline's phase_status comment). Callers combining
    multiple phases (run_city_import_job, run_enrichment_only_job) read
    step_details["source_enrichment_status"] instead of job.status to learn
    what this phase actually concluded."""
    job.step_details = {**dict(job.step_details or {}), "pipeline_counters": counters, "source_enrichment_status": phase_status}
