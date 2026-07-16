"""CITYGO-314: truthful per-step diagnostics.

services/import_pipeline/progress.py::set_step gained an optional db=
parameter — when supplied, it records a durable ImportJobStep row
(started_at/finished_at/status/counters) at exactly the point the caller
already decides a step is starting or finishing, reusing the same
started/finished model already proven in services/import_pipeline_foundation.py.
Every pre-existing caller that does not pass db= keeps its exact prior
behavior (job.current_step/step_details mutation only, no new DB row).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from models.city_admin_import_job import CityAdminImportJob
from services.import_job_step_service import list_job_steps
from services.import_pipeline.progress import set_step


def _job(db_session, city) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", current_step="running")
    db_session.add(job)
    db_session.commit()
    return job


def test_set_step_without_db_does_not_write_import_job_step_new(db_session, city_factory):
    """Backward compatibility: existing callers that never pass db= must
    see zero new ImportJobStep rows — set_step's prior behavior (only
    job.current_step/step_details mutation) is completely unchanged."""
    city = city_factory(slug="step-tracking-no-db")
    job = _job(db_session, city)

    set_step(job, "collecting_places")
    set_step(job, "collecting_places", total=5, processed=5, successful=5)
    db_session.commit()

    assert list_job_steps(db_session, job.id) == []
    assert job.current_step == "collecting_places"
    assert job.total_items == 5


def test_set_step_with_db_records_started_then_terminal_step_new(db_session, city_factory):
    """record_step transitions the SAME row from started -> terminal (see
    services/import_job_step_service.py::_active_step, which matches any
    row for this job_id/step_name still open — finished_at IS NULL) rather
    than creating a second row, so started_at/finished_at land on one
    durable record for a clean duration calculation."""
    city = city_factory(slug="step-tracking-with-db")
    job = _job(db_session, city)

    set_step(job, "collecting_places", db=db_session)
    db_session.commit()
    steps_after_start = list_job_steps(db_session, job.id)
    assert len(steps_after_start) == 1
    assert steps_after_start[0].status == "started"
    assert steps_after_start[0].finished_at is None

    set_step(job, "collecting_places", total=10, processed=10, successful=8, db=db_session)
    db_session.commit()

    steps = list_job_steps(db_session, job.id)
    assert len(steps) == 1
    assert steps[0].status == "success"
    assert steps[0].finished_at is not None
    assert steps[0].counters == {"total": 10, "processed": 10, "successful": 8}


def test_set_step_records_failed_terminal_state_only_when_explicitly_flagged_new(db_session, city_factory):
    """failed=N (items that failed within an otherwise-completed step) must
    never be silently reinterpreted as the step's own terminal status —
    only the explicit step_failed=True flag does that, matching how
    job.failed_items has always been used for per-item counts, not step
    outcome."""
    city = city_factory(slug="step-tracking-failed-items")
    job = _job(db_session, city)

    set_step(job, "finding_addresses", db=db_session)
    db_session.commit()
    set_step(job, "finding_addresses", processed=10, successful=7, failed=3, db=db_session)
    db_session.commit()

    steps = list_job_steps(db_session, job.id)
    assert steps[-1].status == "success"
    assert steps[-1].counters["failed"] == 3


def test_set_step_records_step_failed_flag_as_terminal_failure_new(db_session, city_factory):
    city = city_factory(slug="step-tracking-step-failed")
    job = _job(db_session, city)

    set_step(job, "collecting_places", db=db_session)
    db_session.commit()
    set_step(job, "collecting_places", total=0, processed=0, db=db_session, step_failed=True)
    db_session.commit()

    steps = list_job_steps(db_session, job.id)
    assert steps[-1].status == "failed"


def test_step_started_finished_duration_are_real_timestamps_new(db_session, city_factory):
    city = city_factory(slug="step-tracking-duration")
    job = _job(db_session, city)

    set_step(job, "computing_readiness", db=db_session)
    db_session.commit()
    steps = list_job_steps(db_session, job.id)
    steps[0].started_at = datetime.utcnow() - timedelta(seconds=7)
    db_session.commit()

    set_step(job, "computing_readiness", detail={"readiness_score": 80}, db=db_session)
    db_session.commit()

    steps = list_job_steps(db_session, job.id)
    finished = steps[-1]
    assert finished.finished_at is not None
    assert finished.finished_at >= finished.started_at
    assert finished.counters == {"readiness_score": 80}
