"""Tests for the single-job import diagnostic endpoint/service (mobile-first
diagnostic view). Covers failed/success/cancelled jobs, missing optional
fields, timeline ordering, and job-scope isolation from unrelated logs."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.import_job_step import ImportJobStep
from services.admin_import_job_diagnostic_service import build_import_job_diagnostic
from services.system_log_service import write_system_log


def _create_job(db: Session, *, city_id: int, **kwargs: Any) -> CityAdminImportJob:
    defaults: dict[str, Any] = dict(
        city_id=city_id,
        status="queued",
        source="admin_city_import",
        current_step="created",
    )
    defaults.update(kwargs)
    job = CityAdminImportJob(**defaults)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_missing_job_returns_none_new(db_session: Session) -> None:
    assert build_import_job_diagnostic(db_session, job_id=999999) is None


def test_failed_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-failed")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="failed",
        current_step="error",
        last_error="import-worker safety guard: available host memory (532 MB) is below the configured minimum (550 MB)",
        started_at=datetime.utcnow() - timedelta(seconds=30),
        finished_at=datetime.utcnow(),
    )
    write_system_log(
        db_session, level="info", module="import_worker", message=f"Import worker claiming job #{job.id}",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="error", module="import_worker", message=f"Import worker failed job #{job.id}: boom",
        details={"event": "worker_job_failed", "job_id": job.id, "error": "boom"}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "failed"
    assert diagnostic["failure_reason"] is not None and "532 MB" in diagnostic["failure_reason"]
    assert diagnostic["last_completed_step"] == "error"
    assert diagnostic["duration_seconds"] is not None and diagnostic["duration_seconds"] >= 0
    assert len(diagnostic["timeline"]) == 2
    assert diagnostic["timeline"][0]["type"] == "job_claimed"
    assert diagnostic["timeline"][1]["type"] == "failed"
    assert diagnostic["timeline"][1]["severity"] == "error"
    assert "boom" in diagnostic["diagnostic_report"]
    assert "532 MB" in diagnostic["diagnostic_report"]


def test_successful_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-success")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="success",
        current_step="ready_for_review",
        started_at=datetime.utcnow() - timedelta(minutes=2),
        finished_at=datetime.utcnow(),
        places_found=10,
        places_saved=10,
    )
    write_system_log(
        db_session, level="info", module="city_import", message=f"Импорт #{job.id}: success, мест в городе 10",
        details={"event": "import_job_finished", "job_id": job.id, "places_total": 10}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "success"
    assert diagnostic["failure_reason"] is None
    assert diagnostic["last_completed_step"] == "ready_for_review"
    assert len(diagnostic["timeline"]) == 1
    assert diagnostic["timeline"][0]["type"] == "success"
    assert "success" in diagnostic["diagnostic_report"]


def test_cancelled_job_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-cancelled")
    job = _create_job(
        db_session,
        city_id=city.id,
        status="cancelled",
        current_step="cancelled",
        cancelled_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    write_system_log(
        db_session, level="info", module="city_import", message=f"Импорт #{job.id} отменён без изменения публикации города",
        details={"event": "import_job_cancelled", "job_id": job.id}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "cancelled"
    assert diagnostic["timeline"][0]["type"] == "cancelled"
    assert diagnostic["timeline"][0]["severity"] == "warning"


def test_missing_optional_fields_do_not_break_endpoint_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A freshly-created queued job has no started_at/finished_at/last_error
    and no timeline events yet — the endpoint must still return a complete,
    valid diagnostic with nullable fields as null, not raise."""
    city = city_factory(slug="diag-queued")
    job = _create_job(db_session, city_id=city.id)

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["started_at"] is None
    assert diagnostic["finished_at"] is None
    assert diagnostic["duration_seconds"] is None
    assert diagnostic["failure_reason"] is None
    assert diagnostic["last_completed_step"] is None
    assert diagnostic["worker_state"] is None
    assert diagnostic["worker_run_id"] is None
    assert diagnostic["stop_reason"] is None
    assert diagnostic["exit_code"] is None
    assert diagnostic["oom_killed"] is None
    assert diagnostic["workflow_run_url"] is None
    assert diagnostic["timeline"] == []
    assert diagnostic["diagnostic_report"]


def test_timeline_ordering_is_chronological_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-order")
    job = _create_job(db_session, city_id=city.id, status="running", current_step="collecting_places")
    write_system_log(
        db_session, level="info", module="import_worker", message="first",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="warning", module="import_worker", message="second",
        details={"event": "worker_job_blocked_safe_mode", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="city_import", message="third",
        details={"event": "unified_import_pipeline_finished", "job_id": job.id}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    timestamps = [event["timestamp"] for event in diagnostic["timeline"]]
    assert timestamps == sorted(timestamps)
    assert [event["summary"] for event in diagnostic["timeline"]] == ["first", "second", "third"]


def test_events_from_another_job_are_excluded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-scope")
    job_a = _create_job(db_session, city_id=city.id, status="running")
    job_b = _create_job(db_session, city_id=city.id, status="running")

    write_system_log(
        db_session, level="info", module="import_worker", message=f"claim {job_a.id}",
        details={"event": "worker_job_claimed", "job_id": job_a.id}, request_id=str(job_a.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="import_worker", message=f"claim {job_b.id}",
        details={"event": "worker_job_claimed", "job_id": job_b.id}, request_id=str(job_b.id), commit=True,
    )

    diagnostic_a = build_import_job_diagnostic(db_session, job_id=job_a.id)

    assert diagnostic_a is not None
    assert len(diagnostic_a["timeline"]) == 1
    assert str(job_a.id) in diagnostic_a["timeline"][0]["summary"] or diagnostic_a["timeline"][0]["payload"]["job_id"] == job_a.id


def test_events_from_unrelated_modules_are_excluded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A frontend/health-check/unrelated system log sharing the same
    request_id string coincidentally must not leak into the job timeline —
    only import_worker/city_import modules are included."""
    city = city_factory(slug="diag-unrelated-module")
    job = _create_job(db_session, city_id=city.id, status="running")

    write_system_log(
        db_session, level="info", module="import_worker", message="claimed",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="error", module="frontend", message="unrelated frontend error",
        details={"event": "frontend_error"}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert len(diagnostic["timeline"]) == 1
    assert diagnostic["timeline"][0]["type"] == "job_claimed"


def test_diagnostic_report_is_plain_text_not_raw_json_dump_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-report-text")
    job = _create_job(
        db_session, city_id=city.id, status="failed", current_step="error",
        last_error="boom", started_at=datetime.utcnow(), finished_at=datetime.utcnow(),
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    report = diagnostic["diagnostic_report"]
    assert isinstance(report, str)
    assert not report.strip().startswith("{")
    assert "Job #" in report
    assert city.name in report


def test_api_returns_diagnostic_for_existing_job_new(client, db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-api")
    job = _create_job(db_session, city_id=city.id, status="running", current_step="collecting_places")

    response = client.get(f"/admin/import-jobs/{job.id}/diagnostic")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job.id
    assert body["city_slug"] == "diag-api"
    assert body["status"] == "running"
    assert body["timeline"] == []
    assert body["diagnostic_report"]


def test_api_returns_404_for_missing_job_new(client) -> None:
    response = client.get("/admin/import-jobs/999999/diagnostic")

    assert response.status_code == 404


def test_workflow_run_id_and_url_populate_diagnostic_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-workflow-run")
    job = _create_job(db_session, city_id=city.id, status="running")
    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker run started",
        details={
            "event": "worker_run_started", "job_id": job.id, "worker_run_id": "29192806410",
            "workflow_name": "CITY GO · OPS · Run Import Worker Safely",
            "github_run_id": "29192806410",
            "github_run_url": "https://github.com/GoToValhalla/City-GO/actions/runs/29192806410",
        },
        request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["worker_run_id"] == "29192806410"
    assert diagnostic["workflow_name"] == "CITY GO · OPS · Run Import Worker Safely"
    assert diagnostic["workflow_run_id"] == "29192806410"
    assert diagnostic["workflow_run_url"] == "https://github.com/GoToValhalla/City-GO/actions/runs/29192806410"
    assert diagnostic["worker_state"] == "running"
    assert diagnostic["workflow_run_url"] in diagnostic["diagnostic_report"]


def test_health_degradation_populates_stop_reason_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-health-degraded")
    job = _create_job(db_session, city_id=city.id, status="running")
    write_system_log(
        db_session, level="warning", module="import_worker", message="Import-worker public health check degraded",
        details={
            "event": "worker_health_check_failed", "job_id": job.id,
            "stop_reason": "health_check_failed_health=000_ready=200_streak=1",
        },
        request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["stop_reason"] == "health_check_failed_health=000_ready=200_streak=1"
    assert len(diagnostic["timeline"]) == 1
    assert diagnostic["timeline"][0]["type"] == "health_degradation"
    assert diagnostic["timeline"][0]["severity"] == "warning"


def test_sigterm_and_workflow_cleanup_appear_in_timeline_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-sigterm-cleanup")
    job = _create_job(db_session, city_id=city.id, status="failed", current_step="error")
    write_system_log(
        db_session, level="warning", module="import_worker", message="Import-worker stop requested",
        details={"event": "worker_stop_requested", "job_id": job.id, "stop_reason": "public_health_degraded", "stop_source": "monitor_loop"},
        request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker workflow cleanup executed",
        details={"event": "workflow_cleanup", "job_id": job.id, "stop_reason": "public_health_degraded"},
        request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["stop_reason"] == "public_health_degraded"
    assert diagnostic["stop_source"] == "monitor_loop"
    types = [event["type"] for event in diagnostic["timeline"]]
    assert types == ["sigterm", "workflow_cleanup"]
    assert diagnostic["timeline"][0]["severity"] == "warning"


def test_worker_events_from_another_job_are_excluded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-worker-scope")
    job_a = _create_job(db_session, city_id=city.id, status="running")
    job_b = _create_job(db_session, city_id=city.id, status="running")

    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker run started",
        details={"event": "worker_run_started", "job_id": job_a.id, "worker_run_id": "run-a"},
        request_id=str(job_a.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker run started",
        details={"event": "worker_run_started", "job_id": job_b.id, "worker_run_id": "run-b"},
        request_id=str(job_b.id), commit=True,
    )

    diagnostic_a = build_import_job_diagnostic(db_session, job_id=job_a.id)
    diagnostic_b = build_import_job_diagnostic(db_session, job_id=job_b.id)

    assert diagnostic_a is not None and diagnostic_b is not None
    assert diagnostic_a["worker_run_id"] == "run-a"
    assert diagnostic_b["worker_run_id"] == "run-b"
    assert len(diagnostic_a["timeline"]) == 1
    assert len(diagnostic_b["timeline"]) == 1


def test_partial_success_reason_reflects_failed_non_critical_step_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """partial_success never sets job.last_error (see
    services/import_pipeline_foundation.py) — the real reason lives in the
    per-step ImportJobStep.error_message row instead. The diagnostic must
    surface that reason explicitly rather than leaving the operator to read
    raw step_details JSON."""
    city = city_factory(slug="diag-partial-success")
    job = _create_job(
        db_session, city_id=city.id, status="partial_success", current_step="apply_publication_decisions",
        started_at=datetime.utcnow() - timedelta(minutes=1), finished_at=datetime.utcnow(),
    )
    db_session.add(ImportJobStep(
        job_id=job.id, step_name="fetch_photo_candidates", status="failed",
        error_message="photo provider timed out", finished_at=datetime.utcnow(),
    ))
    db_session.commit()

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "partial_success"
    assert diagnostic["failure_reason"] is None
    assert diagnostic["partial_success_reason"] is not None
    assert "photo provider timed out" in diagnostic["partial_success_reason"]
    assert len(diagnostic["failed_steps"]) == 1
    assert diagnostic["failed_steps"][0]["step_name"] == "fetch_photo_candidates"
    assert diagnostic["failed_steps"][0]["error_message"] == "photo provider timed out"
    assert "Partial success reason" in diagnostic["diagnostic_report"]


def test_partial_success_reason_is_none_when_no_failed_steps_recorded_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A partial_success job with no ImportJobStep rows at all (e.g. legacy
    data, or the run predates step-level recording) must report null, never
    a fabricated reason."""
    city = city_factory(slug="diag-partial-no-steps")
    job = _create_job(db_session, city_id=city.id, status="partial_success", current_step="apply_publication_decisions")

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["partial_success_reason"] is None
    assert diagnostic["failed_steps"] == []


def test_success_job_has_no_partial_success_reason_even_with_failed_steps_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """partial_success_reason must only ever apply to a genuinely
    partial_success job — a plain success job must never show it, even if
    an unrelated failed step row exists from a much earlier retry."""
    city = city_factory(slug="diag-success-with-old-failed-step")
    job = _create_job(db_session, city_id=city.id, status="success", current_step="ready_for_review")
    db_session.add(ImportJobStep(job_id=job.id, step_name="fetch_photo_candidates", status="failed", error_message="stale failure"))
    db_session.commit()

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["partial_success_reason"] is None


def test_no_synthesized_workflow_outcome_field_exists_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """Architecture guard: the diagnostic must never derive or expose a
    synthesized "did the workflow pass" verdict — that would duplicate
    run-import-worker-safe.yml's own fail-closed decision logic as a second,
    driftable decision engine. Only the raw, separately-persisted evidence
    (exit_code, oom_killed, stop_reason) may be exposed; GitHub Actions
    itself remains the sole authority on whether a workflow run passed."""
    city = city_factory(slug="diag-no-workflow-outcome-field")
    job = _create_job(db_session, city_id=city.id, status="success", finished_at=datetime.utcnow())
    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker run finished",
        details={"event": "worker_run_finished", "job_id": job.id, "stop_reason": "timeout", "exit_code": 137, "oom_killed": True},
        request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert "workflow_outcome" not in diagnostic
    assert "Workflow outcome" not in diagnostic["diagnostic_report"]


def test_oom_and_success_status_are_exposed_as_separate_raw_facts_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """job.status=success and the worker's own reported exit_code=137/
    oom_killed=True must both be visible, as-persisted, without the service
    collapsing them into any single derived pass/fail judgment."""
    city = city_factory(slug="diag-oom-vs-job-success")
    job = _create_job(db_session, city_id=city.id, status="success", finished_at=datetime.utcnow())
    write_system_log(
        db_session, level="info", module="import_worker", message="Import-worker run finished",
        details={"event": "worker_run_finished", "job_id": job.id, "stop_reason": "timeout", "exit_code": 137, "oom_killed": True},
        request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["status"] == "success"
    assert diagnostic["exit_code"] == 137
    assert diagnostic["oom_killed"] is True


def test_attempts_are_present_in_diagnostic_payload_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """attempts (the immutable retry-history reconstruction from durable
    system_logs, distinct from the job's own mutable current status/columns)
    must actually appear in the diagnostic output — this field existed in
    the service/schema with zero test coverage before this change."""
    city = city_factory(slug="diag-attempts")
    job = _create_job(db_session, city_id=city.id, status="failed", current_step="error")
    write_system_log(
        db_session, level="info", module="import_worker", message="claim 1",
        details={"event": "worker_job_claimed", "job_id": job.id, "retry_count": 0}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="error", module="import_worker", message="fail 1",
        details={"event": "worker_job_failed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )
    write_system_log(
        db_session, level="info", module="import_worker", message="claim 2",
        details={"event": "worker_job_claimed", "job_id": job.id, "retry_count": 1}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert len(diagnostic["attempts"]) == 2
    assert diagnostic["attempts"][0]["attempt_number"] == 1
    assert diagnostic["attempts"][0]["result"] == "worker_job_failed"
    assert diagnostic["attempts"][0]["retry_count_at_claim"] == 0
    assert diagnostic["attempts"][1]["attempt_number"] == 2
    assert diagnostic["attempts"][1]["result"] == "in_progress"
    assert diagnostic["attempts"][1]["retry_count_at_claim"] == 1


def test_attempts_are_empty_when_job_was_never_claimed_by_worker_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A queued job with zero worker_job_claimed events must show an empty
    attempts list — zero attempts is a genuinely different, truthful state
    from one successful first-try attempt, and must never be inferred."""
    city = city_factory(slug="diag-attempts-empty")
    job = _create_job(db_session, city_id=city.id, status="queued")

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["attempts"] == []


def test_api_diagnostic_response_includes_new_fields_new(client, db_session: Session, city_factory: Callable[..., Any]) -> None:
    """End-to-end contract check: the new fields survive Pydantic response
    serialization through the real HTTP endpoint, not just the raw service
    dict."""
    city = city_factory(slug="diag-api-new-fields")
    job = _create_job(db_session, city_id=city.id, status="partial_success", current_step="apply_publication_decisions")
    db_session.add(ImportJobStep(job_id=job.id, step_name="fetch_photo_candidates", status="failed", error_message="boom"))
    db_session.commit()

    response = client.get(f"/admin/import-jobs/{job.id}/diagnostic")

    assert response.status_code == 200
    body = response.json()
    assert body["partial_success_reason"] is not None
    assert "boom" in body["partial_success_reason"]
    assert body["failed_steps"][0]["step_name"] == "fetch_photo_candidates"
    assert "workflow_outcome" not in body
    assert body["attempts"] == []


def test_api_diagnostic_response_includes_steps_and_funnel_accounting_new(client, db_session: Session, city_factory: Callable[..., Any]) -> None:
    """CITYGO-314/315/316 end-to-end contract check through the real HTTP
    endpoint: steps, funnel, and funnel_accounting all survive Pydantic
    response serialization, not just the raw service dict."""
    city = city_factory(slug="diag-api-funnel-fields")
    job = _create_job(
        db_session, city_id=city.id, status="success", finished_at=datetime.utcnow(),
        step_details={
            "collecting_places": {
                "import_diff": {
                    "funnel": {
                        "requested": 3, "fetched": 3, "deduplicated": "unavailable", "normalized": 3,
                        "accepted": 2, "rejected_by_reason": {"missing_name": 1}, "matched_existing": 0,
                        "created": 2, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 0, "failed": 0,
                    },
                },
            },
        },
    )
    db_session.add(ImportJobStep(
        job_id=job.id, step_name="collecting_places", status="success", counters={"total": 3},
        started_at=datetime.utcnow() - timedelta(seconds=5), finished_at=datetime.utcnow(),
    ))
    db_session.commit()

    response = client.get(f"/admin/import-jobs/{job.id}/diagnostic")

    assert response.status_code == 200
    body = response.json()
    assert body["steps"][0]["step_name"] == "collecting_places"
    assert body["steps"][0]["duration_seconds"] >= 5
    assert body["funnel"]["requested"] == 3
    assert body["funnel_accounting"]["ok"] is True
    assert body["funnel_accounting"]["checked"] is True


def test_missing_lifecycle_events_leave_worker_fields_nullable_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A job that has never had any worker-lifecycle event reported (e.g. it
    was processed by the in-process worker loop without the workflow
    reporting layer, or hasn't been claimed yet) must return null for all
    worker/workflow fields rather than raising or defaulting to a fake value."""
    city = city_factory(slug="diag-no-lifecycle-events")
    job = _create_job(db_session, city_id=city.id, status="running")
    write_system_log(
        db_session, level="info", module="import_worker", message=f"Import worker claiming job #{job.id}",
        details={"event": "worker_job_claimed", "job_id": job.id}, request_id=str(job.id), commit=True,
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["worker_state"] is None
    assert diagnostic["worker_run_id"] is None
    assert diagnostic["stop_reason"] is None
    assert diagnostic["stop_source"] is None
    assert diagnostic["exit_code"] is None
    assert diagnostic["oom_killed"] is None
    assert diagnostic["workflow_name"] is None
    assert diagnostic["workflow_run_id"] is None
    assert diagnostic["workflow_run_url"] is None


# --- CITYGO-316: complete funnel + per-step breakdown exposed in diagnostics ---


def test_diagnostic_exposes_step_breakdown_from_persisted_import_job_steps_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-step-breakdown")
    job = _create_job(db_session, city_id=city.id, status="success", finished_at=datetime.utcnow())
    step = ImportJobStep(
        job_id=job.id, step_name="collecting_places", status="success",
        counters={"total": 10, "processed": 10, "successful": 8},
        started_at=datetime.utcnow() - timedelta(seconds=12),
        finished_at=datetime.utcnow(),
    )
    db_session.add(step)
    db_session.commit()

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert len(diagnostic["steps"]) == 1
    row = diagnostic["steps"][0]
    assert row["step_name"] == "collecting_places"
    assert row["status"] == "success"
    assert row["duration_seconds"] is not None
    assert row["duration_seconds"] >= 12
    assert row["counters"] == {"total": 10, "processed": 10, "successful": 8}


def test_diagnostic_step_duration_is_none_not_zero_when_step_still_running_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-step-still-running")
    job = _create_job(db_session, city_id=city.id, status="running")
    step = ImportJobStep(job_id=job.id, step_name="finding_addresses", status="started", started_at=datetime.utcnow())
    db_session.add(step)
    db_session.commit()

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    row = diagnostic["steps"][0]
    assert row["finished_at"] is None
    assert row["duration_seconds"] is None
    assert row["duration_seconds"] != 0


def test_diagnostic_exposes_funnel_from_job_step_details_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    city = city_factory(slug="diag-funnel-exposed")
    job = _create_job(
        db_session, city_id=city.id, status="success", finished_at=datetime.utcnow(),
        step_details={
            "collecting_places": {
                "import_diff": {
                    "status": "success",
                    "funnel": {
                        "requested": 5, "fetched": 5, "deduplicated": "unavailable", "normalized": 5,
                        "accepted": 4, "rejected_by_reason": {"missing_name": 1}, "matched_existing": 0,
                        "created": 3, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 1, "failed": 0,
                    },
                },
            },
        },
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["funnel"]["requested"] == 5
    assert diagnostic["funnel"]["rejected_by_reason"] == {"missing_name": 1}
    assert diagnostic["funnel_accounting"]["ok"] is True
    assert diagnostic["funnel_accounting"]["checked"] is True


def test_diagnostic_funnel_and_accounting_are_none_before_any_run_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """A queued job that has never produced a funnel must not show a fake
    zero funnel or a fake accounting pass — both must be None/unchecked."""
    city = city_factory(slug="diag-funnel-not-yet")
    job = _create_job(db_session, city_id=city.id, status="queued")

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["funnel"] is None
    assert diagnostic["funnel_accounting"]["checked"] is False
    assert diagnostic["funnel_accounting"]["ok"] is False
    assert diagnostic["funnel_accounting"]["reason"] == "funnel_missing"


def test_diagnostic_surfaces_accounting_mismatch_without_hiding_it_new(db_session: Session, city_factory: Callable[..., Any]) -> None:
    """If a funnel is ever internally inconsistent, the diagnostic must
    surface that truthfully — not silently correct it or hide it."""
    city = city_factory(slug="diag-funnel-mismatch")
    job = _create_job(
        db_session, city_id=city.id, status="success", finished_at=datetime.utcnow(),
        step_details={
            "collecting_places": {
                "import_diff": {
                    "funnel": {
                        "requested": 99, "fetched": 5, "deduplicated": "unavailable", "normalized": 5,
                        "accepted": 4, "rejected_by_reason": {"missing_name": 1}, "matched_existing": 0,
                        "created": 3, "updated": 0, "unchanged": 0, "hidden": 0, "sent_to_review": 1, "failed": 0,
                    },
                },
            },
        },
    )

    diagnostic = build_import_job_diagnostic(db_session, job_id=job.id)

    assert diagnostic is not None
    assert diagnostic["funnel_accounting"]["checked"] is True
    assert diagnostic["funnel_accounting"]["ok"] is False
    assert diagnostic["funnel_accounting"]["reason"] == "accounting_mismatch"
    assert diagnostic["funnel_accounting"]["requested_equation"]["requested"] == 99
