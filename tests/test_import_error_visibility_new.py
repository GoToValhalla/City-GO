"""Error/log visibility and report-only snapshot/publication consistency checks."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.system_log import SystemLog
from services.admin_city_import_job_payload import SNAPSHOT_KEY, build_import_job_payload
from services.admin_import_display import pipeline_warnings, publication_consistency_warning, snapshot_warning
from services.import_pipeline import runner as import_runner


def test_failed_import_job_exposes_error_reason_in_admin_payload_new(db_session, city_factory) -> None:
    city = city_factory(slug="error-visibility-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(
        city_id=city.id,
        status="failed",
        source="admin_city_import",
        current_step="error",
        last_error="tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist",
        step_details={"warnings": [{"step": "collecting_places", "error": "tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist"}]},
    )
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    assert payload["import_error_summary"] is not None
    assert "UndefinedColumn" in payload["import_error_summary"]["error_message"]
    assert payload["import_error_summary"]["primary_error_kind"] == "schema_mismatch"


def test_job_with_errors_shows_classified_warning_not_bare_error_string_new(db_session, city_factory) -> None:
    city = city_factory(slug="warning-classification-city", launch_status="review_required", is_active=False)
    job = CityAdminImportJob(
        city_id=city.id,
        status="success_with_warnings",
        source="admin_city_import",
        step_details={"warnings": [{"step": "finding_addresses", "error": "urlopen error timed out"}]},
    )
    db_session.add(job)
    db_session.commit()

    warnings = pipeline_warnings(job)

    assert len(warnings) == 1
    assert warnings[0]["kind"] == "source_failure"
    assert warnings[0]["retryable"] is True
    assert warnings[0]["admin_hint"]


def test_pipeline_failure_writes_a_diagnostic_log_event_not_only_lifecycle_new(db_session, city_factory, monkeypatch) -> None:
    """The except-block in run_enrichment_pipeline must not swallow the real
    exception without an admin-visible system_log entry (module=city_import)."""
    city = city_factory(slug="diagnostic-log-city", launch_status="importing", is_active=False)
    place = Place(city_id=city.id, slug="diagnostic-log-place", title="Diagnostic Log Place", lat=54.7, lng=20.5, category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add_all([place, job])
    db_session.commit()

    def fake_run_osm_import_only(*_args, **_kwargs):
        raise RuntimeError("tourist_core: psycopg.errors.UndefinedColumn: column places.place_layer does not exist")

    monkeypatch.setattr(import_runner, "run_osm_import_only", fake_run_osm_import_only)
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_args, **_kwargs: None)

    import_runner.run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)

    diagnostic_logs = (
        db_session.query(SystemLog)
        .filter(SystemLog.module == "city_import", SystemLog.level == "error")
        .all()
    )
    assert len(diagnostic_logs) >= 1
    failure_log = diagnostic_logs[-1]
    assert failure_log.details.get("event") == "import_pipeline_failed"
    assert "UndefinedColumn" in failure_log.details.get("error", "")
    assert failure_log.details.get("kind") == "schema_mismatch"
    assert failure_log.details.get("job_id") == job.id
    assert failure_log.details.get("city_id") == city.id
    assert failure_log.details.get("step")


def test_snapshot_missing_is_reported_only_new(db_session, city_factory) -> None:
    result = snapshot_warning(None)
    assert result is not None
    assert result["code"] == "SNAPSHOT_MISSING"


def test_snapshot_missing_is_not_reported_for_a_queued_job_new(db_session, city_factory) -> None:
    """A queued/running job has not had a chance to produce a snapshot yet —
    flagging that as SNAPSHOT_MISSING would just be noise, not a real inconsistency."""
    city = city_factory(slug="snapshot-queued-city", launch_status="importing", is_active=False)
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    assert payload["snapshot_warning"] is None


def test_snapshot_missing_is_reported_for_a_stalled_job_without_snapshot_new(db_session, city_factory) -> None:
    """Unlike a queued job, a job that actually finished (even by failing/stalling)
    and never produced a snapshot is a genuine inconsistency to surface."""
    city = city_factory(slug="snapshot-stalled-city", launch_status="import_failed", is_active=False)
    job = CityAdminImportJob(city_id=city.id, status="stalled", source="admin_city_import", current_step="error", step_details={})
    db_session.add(job)
    db_session.commit()

    payload = build_import_job_payload(db_session, city)

    assert payload["snapshot_warning"] is not None
    assert payload["snapshot_warning"]["code"] == "SNAPSHOT_MISSING"


def test_snapshot_stale_is_reported_only_new() -> None:
    old_snapshot = {"taken_at": (datetime.utcnow() - timedelta(hours=48)).isoformat(), "data_coverage": {"places_total": 10}}

    result = snapshot_warning(old_snapshot)

    assert result is not None
    assert result["code"] == "SNAPSHOT_STALE"


def test_snapshot_empty_coverage_is_reported_only_new() -> None:
    empty_snapshot = {"taken_at": datetime.utcnow().isoformat(), "data_coverage": {"places_total": 0}}

    result = snapshot_warning(empty_snapshot)

    assert result is not None
    assert result["code"] == "SNAPSHOT_EMPTY_COVERAGE"


def test_fresh_snapshot_with_coverage_is_not_reported_new() -> None:
    fresh_snapshot = {"taken_at": datetime.utcnow().isoformat(), "data_coverage": {"places_total": 42}}

    assert snapshot_warning(fresh_snapshot) is None


def test_published_city_with_failed_latest_import_is_reported_only_new(db_session, city_factory) -> None:
    city = city_factory(slug="published-failed-import-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="boom")
    db_session.add(job)
    db_session.commit()

    warning = publication_consistency_warning(city, job)

    assert warning is not None
    assert warning["code"] == "PUBLISHED_CITY_LATEST_IMPORT_FAILED"
    assert warning["job_status"] == "failed"
    db_session.refresh(city)
    assert city.launch_status == "published"
    assert city.is_active is True


def test_published_city_with_healthy_latest_import_is_not_reported_new(db_session, city_factory) -> None:
    city = city_factory(slug="published-healthy-import-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    assert publication_consistency_warning(city, job) is None


def test_admin_job_details_read_does_not_mutate_city_or_job_state_new(db_session, city_factory) -> None:
    city = city_factory(slug="read-only-city", launch_status="published", is_active=True)
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="boom")
    db_session.add(job)
    db_session.commit()
    before_launch_status = city.launch_status
    before_is_active = city.is_active
    before_job_status = job.status

    build_import_job_payload(db_session, city)

    db_session.refresh(city)
    db_session.refresh(job)
    assert city.launch_status == before_launch_status
    assert city.is_active == before_is_active
    assert job.status == before_job_status
