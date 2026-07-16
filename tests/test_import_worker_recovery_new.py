from __future__ import annotations

from datetime import datetime, timedelta

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import queue_city_import_job
from services.admin_city_import_tasks import mark_stalled_import_jobs
from services.admin_import_display import effective_failed_items, job_execution_failed, resolve_import_display
from services.system_log_service import list_system_logs, write_system_log


def test_queued_import_job_is_not_displayed_as_failed_from_pending_scope_counters(db_session, city_factory):
    city = city_factory(slug="zelenogradsk", launch_status="published", is_active=True)
    job = CityAdminImportJob(
        city_id=city.id,
        status="queued",
        source="admin_city_import",
        scopes_total=3,
        scopes_succeeded=0,
        current_step="queued",
    )
    db_session.add(job)
    db_session.commit()

    display = resolve_import_display(city, job)

    assert display["status_group"] == "queued"
    assert display["job_execution_failed"] is False
    assert job_execution_failed(job) is False
    assert effective_failed_items(job) == 0


def test_import_log_filter_alias_reads_city_import_records(db_session):
    write_system_log(
        db_session,
        level="info",
        module="city_import",
        message="worker picked queued import job",
        details={"event": "import_worker_job_picked", "job_id": 9},
        city_slug="zelenogradsk",
    )

    rows, total = list_system_logs(db_session, module="import", city_slug="zelenogradsk")

    assert total == 1
    assert rows[0].module == "city_import"


def test_mark_stalled_import_job_preserves_published_destination_state(db_session, city_factory):
    city = city_factory(slug="zelenogradsk", launch_status="published", is_active=True)
    job = CityAdminImportJob(
        city_id=city.id,
        status="running",
        source="admin_city_import",
        current_step="collecting_places",
        updated_at=datetime.utcnow() - timedelta(hours=3),
    )
    db_session.add(job)
    db_session.commit()

    stalled = mark_stalled_import_jobs(db_session, actor_id="test-worker")
    db_session.refresh(city)
    db_session.refresh(job)

    assert stalled == 1
    assert job.status == "stalled"
    assert city.launch_status == "published"
    assert city.is_active is True


def test_queue_city_import_job_creates_new_row_after_previous_failure(db_session, city_factory):
    """Immutable lifecycle: a new launch after a terminal failure creates a
    brand-new row (previous_job_id pointing at the failed one) rather than
    resetting the failed row in place — see
    services/admin_city_import_job_service.py and
    tests/test_import_job_lifecycle_new.py for the full contract."""
    city = city_factory(slug="zelenogradsk", launch_status="published", is_active=True)
    job = CityAdminImportJob(
        city_id=city.id,
        status="failed",
        source="admin_city_import",
        current_step="error",
        scopes_total=3,
        scopes_succeeded=0,
        failed_items=3,
        last_error="old failure",
        step_details={"warnings": [{"step": "collecting_places", "error": "old"}]},
        finished_at=datetime.utcnow(),
    )
    db_session.add(job)
    db_session.commit()

    queued = queue_city_import_job(db_session, city_id=city.id, actor_id="test-admin")
    db_session.commit()

    assert queued.id != job.id
    assert queued.previous_job_id == job.id
    assert queued.status == "queued"
    assert queued.current_step == "queued"
    assert queued.failed_items == 0
    assert queued.last_error is None
    assert "warnings" not in dict(queued.step_details or {})
    # the old row is untouched — history is never rewritten
    db_session.refresh(job)
    assert job.status == "failed"
    assert job.last_error == "old failure"
