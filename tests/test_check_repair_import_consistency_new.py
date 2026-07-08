"""DB consistency check/repair script: dry-run vs apply, detection correctness."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import SNAPSHOT_KEY
from data.scripts import check_repair_import_consistency
from data.scripts.check_repair_import_consistency import (
    _check_city_stats_mismatch,
    _check_completed_jobs_without_snapshot,
    _check_published_cities_missing_snapshot,
    _check_published_cities_with_failed_import,
    _check_stale_running_jobs,
)


class _NonClosingSessionWrapper:
    """Lets a test's db_session stand in for `with SessionLocal() as db:` without
    the real __exit__ closing the shared test session/connection."""

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


def _stuck_job(db_session, city, *, hours_ago: float = 1) -> CityAdminImportJob:
    started = datetime.utcnow() - timedelta(hours=hours_ago)
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", current_step="collecting_places", started_at=started, updated_at=started)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_dry_run_does_not_mutate_db_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-dry-run-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=1)
    before_status = job.status
    before_updated_at = job.updated_at

    result = _check_stale_running_jobs(db_session, apply_mode=False, actor_id="test")

    assert result["count"] == 1
    assert result["repaired"] == 0
    db_session.refresh(job)
    assert job.status == before_status
    assert job.updated_at == before_updated_at


def test_stale_running_job_is_detected_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-detect-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=1)

    result = _check_stale_running_jobs(db_session, apply_mode=False, actor_id="test")

    assert result["count"] == 1
    assert result["found"][0]["job_id"] == job.id
    assert result["found"][0]["city_id"] == city.id


def test_apply_stale_running_job_is_idempotent_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-apply-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=1)

    first = _check_stale_running_jobs(db_session, apply_mode=True, actor_id="test")
    assert first["count"] == 1
    assert first["repaired"] == 1

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.current_step == "error"

    second = _check_stale_running_jobs(db_session, apply_mode=True, actor_id="test")
    assert second["count"] == 0
    assert second["repaired"] == 0

    db_session.refresh(job)
    assert job.status == "stalled"
    assert job.current_step == "error"


def test_completed_job_without_snapshot_is_reported_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-no-snapshot-city", launch_status="review_required", is_active=False)
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import", current_step="ready_for_review", step_details={})
    db_session.add(job)
    db_session.commit()

    result = _check_completed_jobs_without_snapshot(db_session)

    assert result["count"] == 1
    assert result["found"][0]["job_id"] == job.id
    assert result["repaired"] == 0


def test_completed_job_with_snapshot_is_not_reported_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-has-snapshot-city", launch_status="review_required", is_active=False)
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import", current_step="ready_for_review", step_details={SNAPSHOT_KEY: {"data_coverage": {}}})
    db_session.add(job)
    db_session.commit()

    result = _check_completed_jobs_without_snapshot(db_session)

    assert result["count"] == 0


def test_published_city_without_snapshot_is_reported_and_not_unpublished_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-published-no-snapshot-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import", step_details={})
    db_session.add(job)
    db_session.commit()

    result = _check_published_cities_missing_snapshot(db_session)

    assert result["count"] == 1
    assert result["found"][0]["city_id"] == city.id
    db_session.refresh(city)
    assert city.launch_status == "published"
    assert city.is_active is True


def test_latest_failed_import_on_published_city_is_reported_new(db_session, city_factory) -> None:
    city = city_factory(slug="consistency-published-failed-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="boom")
    db_session.add(job)
    db_session.commit()

    result = _check_published_cities_with_failed_import(db_session)

    assert result["count"] == 1
    assert result["found"][0]["city_id"] == city.id
    assert result["found"][0]["job_status"] == "failed"
    db_session.refresh(city)
    assert city.launch_status == "published"
    assert city.is_active is True


def test_city_stats_mismatch_is_reported_only_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="consistency-stats-mismatch-city", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="consistency-stats-place-1", title="Place 1")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import", places_saved=99)
    db_session.add(job)
    db_session.commit()

    result = _check_city_stats_mismatch(db_session)

    row = next(item for item in result["found"] if item["city_id"] == city.id)
    assert row["job_places_saved"] == 99
    assert row["actual_places"] == 1
    assert result["repaired"] == 0
    assert "no existing safe stats-repair helper" in result["note"]


def test_run_end_to_end_dry_run_reports_without_mutating_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="consistency-e2e-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=1)
    monkeypatch.setattr(check_repair_import_consistency, "SessionLocal", lambda: _NonClosingSessionWrapper(db_session))

    report = check_repair_import_consistency.run(["--dry-run"])

    assert report["mode"] == "dry_run"
    assert report["stale_running_jobs"]["count"] == 1
    assert report["stale_running_jobs"]["repaired"] == 0
    db_session.refresh(job)
    assert job.status == "running"


def test_run_end_to_end_apply_repairs_stale_job_new(db_session, city_factory, monkeypatch) -> None:
    city = city_factory(slug="consistency-e2e-apply-city", launch_status="importing", is_active=False)
    job = _stuck_job(db_session, city, hours_ago=1)
    monkeypatch.setattr(check_repair_import_consistency, "SessionLocal", lambda: _NonClosingSessionWrapper(db_session))

    report = check_repair_import_consistency.run(["--apply"])

    assert report["mode"] == "apply"
    assert report["stale_running_jobs"]["repaired"] == 1
    db_session.refresh(job)
    assert job.status == "stalled"
