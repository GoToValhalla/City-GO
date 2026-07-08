from __future__ import annotations

from datetime import datetime, timedelta

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.import_pipeline.progress import is_stalled, set_current_scope, worker_progress_snapshot
from services.import_pipeline.steps import STALL_THRESHOLD_MINUTES, STEP_COLLECTING_PLACES


def _running_job(db_session, city_id: int) -> CityAdminImportJob:
    now = datetime.utcnow()
    job = CityAdminImportJob(
        city_id=city_id,
        status="running",
        source="admin_city_import",
        current_step=STEP_COLLECTING_PLACES,
        started_at=now,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_set_current_scope_writes_heartbeat_during_long_collecting_places_new(db_session, city_factory) -> None:
    city = city_factory(slug="progress-scope-city")
    job = _running_job(db_session, city.id)
    before_heartbeat = job.updated_at

    set_current_scope(job, scope_code="tourist_core", scope_name="Туристическое ядро")
    db_session.commit()
    db_session.refresh(job)

    assert job.updated_at != before_heartbeat
    assert job.step_details["current_scope_code"] == "tourist_core"
    assert job.step_details["current_scope_name"] == "Туристическое ядро"
    assert job.step_details["step_started_at"] is not None

    # A second scope starting later must refresh the heartbeat again (simulates
    # the worker moving from one scope to the next during collecting_places).
    first_heartbeat = job.updated_at
    set_current_scope(job, scope_code="food_area", scope_name="Еда и кофе")
    db_session.commit()
    db_session.refresh(job)
    assert job.updated_at >= first_heartbeat
    assert job.step_details["current_scope_code"] == "food_area"


def test_worker_progress_is_not_stale_when_heartbeat_is_recent_new(db_session, city_factory) -> None:
    city = city_factory(slug="progress-fresh-city")
    job = _running_job(db_session, city.id)
    set_current_scope(job, scope_code="tourist_core", scope_name="Туристическое ядро")
    db_session.commit()
    db_session.refresh(job)

    snapshot = worker_progress_snapshot(job)

    assert snapshot is not None
    assert snapshot["is_stale"] is False
    assert snapshot["current_scope_code"] == "tourist_core"
    assert snapshot["current_step"] == STEP_COLLECTING_PLACES
    assert snapshot["running_for_seconds"] is not None
    assert snapshot["current_step_running_for_seconds"] is not None
    assert snapshot["stale_after_seconds"] == STALL_THRESHOLD_MINUTES * 60
    assert "не обновлял" not in snapshot["admin_hint"]
    assert is_stalled(job) is False


def test_worker_progress_is_stale_when_heartbeat_older_than_threshold_new(db_session, city_factory) -> None:
    city = city_factory(slug="progress-stale-city")
    job = _running_job(db_session, city.id)
    set_current_scope(job, scope_code="tourist_core", scope_name="Туристическое ядро")
    stale_time = datetime.utcnow() - timedelta(minutes=STALL_THRESHOLD_MINUTES + 5)
    job.updated_at = stale_time
    db_session.commit()
    db_session.refresh(job)

    snapshot = worker_progress_snapshot(job)

    assert snapshot is not None
    assert snapshot["is_stale"] is True
    assert "не обновлял" in snapshot["admin_hint"]
    assert is_stalled(job) is True


def test_worker_progress_snapshot_is_none_for_finished_job_new(db_session, city_factory) -> None:
    city = city_factory(slug="progress-finished-city")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    assert worker_progress_snapshot(job) is None
    assert worker_progress_snapshot(None) is None


def test_admin_import_job_payload_exposes_worker_progress_fields_new(db_session, city_factory) -> None:
    from services.admin_city_import_job_payload import build_import_job_payload

    city = city_factory(slug="progress-payload-city", launch_status="importing", is_active=False)
    job = _running_job(db_session, city.id)
    set_current_scope(job, scope_code="tourist_core", scope_name="Туристическое ядро")
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    progress = payload["worker_progress"]
    assert progress is not None
    assert progress["current_step"] == STEP_COLLECTING_PLACES
    assert progress["current_scope_code"] == "tourist_core"
    assert progress["current_scope_name"] == "Туристическое ядро"
    assert "is_stale" in progress
    assert "running_for_seconds" in progress
    assert "current_step_running_for_seconds" in progress
    assert "stale_after_seconds" in progress
    assert "last_heartbeat_at" in progress
    assert "admin_hint" in progress


class _NonClosingSessionWrapper:
    """Lets a test's db_session stand in for `with SessionLocal() as db:` without
    the real __exit__ closing the shared test session/connection."""

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_mark_current_scope_writes_scope_and_name_new(db_session, city_factory, monkeypatch) -> None:
    from data.scripts import run_due_import_jobs
    from models.city_import_scope import CityImportScope

    city = city_factory(slug="progress-mark-scope-city")
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Туристическое ядро", priority=1, status="active", enabled=True, import_profile="default")
    db_session.add(scope)
    job = _running_job(db_session, city.id)
    db_session.commit()

    monkeypatch.setattr(run_due_import_jobs, "SessionLocal", lambda: _NonClosingSessionWrapper(db_session))

    run_due_import_jobs._mark_current_scope({"city": city.slug, "scope": "tourist_core", "city_admin_import_job_id": job.id})

    db_session.refresh(job)
    assert job.step_details["current_scope_code"] == "tourist_core"
    assert job.step_details["current_scope_name"] == "Туристическое ядро"


def test_mark_current_scope_is_a_no_op_without_job_id_new(db_session, city_factory) -> None:
    from data.scripts import run_due_import_jobs

    city = city_factory(slug="progress-no-job-id-city")
    # No city_admin_import_job_id in target (e.g. cron-triggered run, not admin-triggered).
    run_due_import_jobs._mark_current_scope({"city": city.slug, "scope": "tourist_core"})


def test_admin_import_queue_polling_endpoint_stays_lightweight_new(client, db_session, city_factory) -> None:
    """GET /admin/import-queue must expose per-running-job progress without any
    extra DB query beyond the jobs it already loads for the queue summary."""
    from sqlalchemy import event

    city = city_factory(slug="progress-queue-city")
    job = _running_job(db_session, city.id)
    set_current_scope(job, scope_code="tourist_core", scope_name="Туристическое ядро")
    db_session.commit()

    query_count = {"n": 0}

    def _before_execute(conn, clauseelement, multiparams, params, execution_options):
        if "select" in str(clauseelement).lower():
            query_count["n"] += 1

    event.listen(db_session.get_bind(), "before_execute", _before_execute)
    try:
        response = client.get("/admin/import-queue")
    finally:
        event.remove(db_session.get_bind(), "before_execute", _before_execute)

    assert response.status_code == 200
    payload = response.json()
    running_progress = next(item for item in payload["running_jobs_progress"] if item["job_id"] == job.id)
    assert running_progress["current_scope_code"] == "tourist_core"
    assert running_progress["is_stale"] is False
    # queue summary already does a fixed, small number of queries (counts + two
    # .all() scans over the tiny jobs table); progress fields must add zero more.
    assert query_count["n"] <= 6
