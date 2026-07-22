from datetime import datetime

from models.city_admin_import_job import CityAdminImportJob
from services import admin_city_import_job_service as service


def _claimed_job(db_session, *, city_id, source, current_step="queued"):
    """Simulates the row exactly as claim_queued_job would have left it —
    status="running", started_at set — since run_city_import_job/
    run_enrichment_only_job no longer perform their own queued -> running
    transition (see admin_city_import_job_service.claim_queued_job)."""
    job = CityAdminImportJob(city_id=city_id, status="running", source=source, current_step=current_step, started_at=datetime.utcnow())
    db_session.add(job)
    db_session.commit()
    return job


def test_city_import_runs_collection_then_source_enrichment_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    city = city_factory(slug="unified-pipeline")
    place_factory(city_id=city.id, slug="unified-place", title="Unified Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)
    calls: list[str] = []

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        calls.append("collection")
        assert notify_completion is False
        return {"import": {"places_saved": 1}, "status": "success", "changed_place_ids": []}

    def fake_source_enrichment(db, *, city, job, actor):
        calls.append("source_enrichment")
        job.step_details = {**dict(job.step_details or {}), "source_enrichment_status": "success"}
        return {"found": 1, "fields_enriched": 2, "provider_errors": 0}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 80})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert calls == ["collection", "source_enrichment"]
    assert result.status == "success"
    assert result.source == service.SOURCE_FULL_IMPORT
    assert result.step_details["unified_pipeline"]["source_enrichment"]["fields_enriched"] == 2
    assert result.step_details["unified_pipeline"]["readiness_score"] == 80
    assert result.step_details["unified_pipeline"]["completed"] is True


def test_enrichment_queue_alias_uses_full_import_source_new(db_session, city_factory) -> None:
    city = city_factory(slug="unified-alias")

    job = service.queue_city_enrichment_job(db_session, city_id=city.id, actor_id="qa")

    assert job.status == "queued"
    assert job.source == service.SOURCE_FULL_IMPORT


def test_foundation_failure_is_not_reported_as_success_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """A critical foundation-stage failure must not be silently upgraded to
    success just because the outer job-finalize step always ran to completion."""

    city = city_factory(slug="foundation-failure-pipeline")
    place_factory(city_id=city.id, slug="foundation-failure-place", title="Foundation Failure Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        return {"import": {"places_saved": 1}, "status": "success", "changed_place_ids": []}

    def fake_source_enrichment(db, *, city, job, actor):
        job.last_error = "critical provider setup failure"
        job.step_details = {**dict(job.step_details or {}), "source_enrichment_status": "failed"}
        return {"found": 1, "failed": 1}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 0})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status == "failed"
    assert any(w.get("step") == "source_enrichment" for w in result.step_details["warnings"])


def test_legacy_collection_partial_failure_is_not_reported_as_success_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """A partial failure in the legacy collection/enrichment stage must survive
    into the final job status, not be overwritten by the unconditional
    success/success_with_warnings assignment at the end of the pipeline."""

    city = city_factory(slug="legacy-partial-pipeline")
    place_factory(city_id=city.id, slug="legacy-partial-place", title="Legacy Partial Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        job.last_error = "some import scopes failed"
        return {"import": {"places_saved": 1}, "status": "partial_success", "changed_place_ids": []}

    def fake_source_enrichment(db, *, city, job, actor):
        job.step_details = {**dict(job.step_details or {}), "source_enrichment_status": "success"}
        return {"found": 1, "fields_enriched": 0, "provider_errors": 0}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 80})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status == "partial_success"
    assert any(w.get("step") == "collection_and_legacy_enrichment" for w in result.step_details["warnings"])


def test_run_exception_does_not_hide_as_partial_success_for_unrelated_old_places_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """A hard exception in this run must be reported as failed even if the city
    already has unrelated places from a previous, unrelated successful run —
    the presence of old data must not launder this run's own failure."""

    city = city_factory(slug="exception-with-old-places")
    place_factory(city_id=city.id, slug="pre-existing-place", title="Pre Existing Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    def fake_collection_raises(db, *, job, city, actor_id, force, notify_completion=True):
        raise RuntimeError("provider setup failed")

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection_raises)

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status == "failed"
    assert result.last_error and "provider setup failed" in result.last_error


def test_import_scope_dns_error_finalizes_job_as_partial_or_failed_new(
    db_session,
    city_factory,
    monkeypatch,
) -> None:
    """Reproduces the Kaliningrad incident shape: all configured scopes
    (e.g. tourist_core) fail with a provider/DNS error and zero places are
    found/saved. The job must land as failed (per existing scopes_total>0,
    scopes_succeeded==0 semantics), never success and never stuck running,
    with the scope error visible and scopes_failed/error_count > 0."""

    city = city_factory(slug="kaliningrad-like-dns-failure")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    dns_error = "Failed to resolve overpass-api.de: [Errno -2] Name or service not known"

    def fake_collection_all_scopes_fail(db, *, job, city, actor_id, force, notify_completion=True):
        job.last_error = f"tourist_core: {dns_error}"
        job.scopes_total = 3
        job.scopes_succeeded = 0
        job.places_found = 0
        job.places_saved = 0
        job.step_details = {
            **dict(job.step_details or {}),
            "warnings": [{"step": "collecting_places", "error": job.last_error, "kind": "scope_failure"}],
        }
        db.commit()
        return {"import": {"scopes_total": 3, "scopes_succeeded": 0, "last_error": job.last_error}, "status": "failed", "changed_place_ids": []}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection_all_scopes_fail)

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status in {"failed", "partial_success"}
    assert result.status != "success"
    assert result.status != "running"
    assert result.last_error
    assert dns_error in result.last_error
    assert result.scopes_total == 3
    assert result.scopes_succeeded == 0
    scope_warnings = [w for w in result.step_details.get("warnings", []) if w.get("step") == "collection_and_legacy_enrichment"]
    assert scope_warnings, "scope failure must remain visible on the finalized job"


def test_enrichment_only_foundation_failure_is_not_reported_as_success_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    city = city_factory(slug="enrichment-only-foundation-failure")
    place_factory(city_id=city.id, slug="enrichment-only-place", title="Enrichment Only Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_ENRICHMENT_ONLY)

    def fake_enrichment_only(db, *, job, city, actor_id):
        job.step_details = {**dict(job.step_details or {}), "changed_place_ids": []}
        db.commit()
        return {"status": "success"}

    def fake_source_enrichment(db, *, city, job, actor):
        job.last_error = "critical provider setup failure"
        job.step_details = {**dict(job.step_details or {}), "source_enrichment_status": "failed"}
        return {"found": 1, "failed": 1}

    monkeypatch.setattr(service, "run_enrichment_only_pipeline", fake_enrichment_only)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)

    result = service.run_enrichment_only_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status == "failed"


def test_real_full_pipeline_leaves_finished_at_null_until_finalize_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """Production Job #10 reproduction, end-to-end: calls the REAL
    run_enrichment_pipeline (not a fake_collection stand-in like the other
    tests in this file) through the real run_city_import_job, mocking only
    its external I/O boundaries (OSM fetch, address/image enrichment,
    readiness). Before the fix, run_enrichment_pipeline itself committed
    job.finished_at while job.status stayed "running"; by the time
    run_city_import_job reached its own finalize_import_job call,
    finalize's `job.finished_at is None` check was already false, so it
    deterministically rejected with reason="already_terminalized" and the
    job was left status="running" forever, even though the pipeline had
    genuinely finished. This must now reach a real terminal status."""
    from services.import_pipeline import runner as import_runner

    city = city_factory(slug="real-pipeline-job10-repro")
    place_factory(city_id=city.id, slug="job10-place", title="Job10 Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    monkeypatch.setattr(import_runner, "run_osm_import_only", lambda *_a, **_k: {
        "results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 1, "created": 1, "updated": 0}}],
    })
    monkeypatch.setattr(import_runner, "run_address_backfill", lambda *_a, **_k: {"checked": 1, "updated": 1, "errors": 0})
    monkeypatch.setattr(import_runner, "run_image_enrich", lambda *_a, **_k: {"scanned_places": 1, "created": 0, "failed": 0})
    monkeypatch.setattr(import_runner, "normalize_places_categories", lambda *_a, **_k: {"scanned": 1, "updated": 0})
    monkeypatch.setattr(import_runner, "compute_city_readiness", lambda *_a, **_k: {"readiness_score": 0.9})
    monkeypatch.setattr(import_runner, "send_admin_alert", lambda **_k: {"sent": True})
    monkeypatch.setattr(import_runner, "_try_refresh_snapshot", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 0.9})
    monkeypatch.setattr(service, "run_foundation_pipeline", lambda **_k: {"found": 0, "failed": 0})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status in {"success", "success_with_warnings"}
    assert result.finished_at is not None
    assert result.status != "running"


def test_real_enrichment_only_leaves_finished_at_null_until_finalize_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """Same Job #10 shape as the full-pipeline test above, but through the
    real run_enrichment_only_pipeline / run_enrichment_only_job path
    (services/import_pipeline/enrichment_only.py had the identical
    finished_at-committed-before-finalize defect)."""
    from services.import_pipeline import enrichment_only as import_enrichment_only

    city = city_factory(slug="real-enrichment-only-job10-repro")
    place_factory(city_id=city.id, slug="job10-enrichment-place", title="Job10 Enrichment Place", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_ENRICHMENT_ONLY)

    monkeypatch.setattr(import_enrichment_only, "run_address_backfill", lambda *_a, **_k: {"checked": 1, "updated": 1, "errors": 0, "last_scanned_place_id": 0})
    monkeypatch.setattr(import_enrichment_only, "run_image_enrich", lambda *_a, **_k: {"scanned_places": 1, "created": 0, "errors": [], "last_scanned_place_id": 0})
    monkeypatch.setattr(import_enrichment_only, "run_quality_cleanup", lambda *_a, **_k: {"updated": 1})
    monkeypatch.setattr(import_enrichment_only, "normalize_city_categories", lambda *_a, **_k: {"scanned": 1, "updated": 0})
    monkeypatch.setattr(import_enrichment_only, "compute_city_readiness", lambda *_a, **_k: {"readiness_score": 0.9})
    monkeypatch.setattr(import_enrichment_only, "send_admin_alert", lambda **_k: {"sent": True})
    monkeypatch.setattr(service, "run_foundation_pipeline", lambda **_k: {"found": 0, "failed": 0})

    result = service.run_enrichment_only_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.status in {"success", "success_with_warnings"}
    assert result.finished_at is not None
    assert result.status != "running"


def test_no_pipeline_phase_can_return_running_with_finished_at_set_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """Direct invariant check on the real phase functions in isolation
    (not through the outer finalize path): status="running" and
    finished_at != NULL together is the exact contradiction that made
    finalize_import_job reject every single time, deterministically. Both
    real pipeline phase functions must never produce this combination."""
    from services.import_pipeline.enrichment_only import run_enrichment_only_pipeline
    from services.import_pipeline.runner import run_enrichment_pipeline

    city = city_factory(slug="no-running-with-finished-at-full")
    place_factory(city_id=city.id, slug="invariant-place-full", title="Invariant Place Full", category="park")
    job = _claimed_job(db_session, city_id=city.id, source=service.SOURCE_FULL_IMPORT)

    monkeypatch.setattr("services.import_pipeline.runner.run_osm_import_only", lambda *_a, **_k: {
        "results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 1, "created": 1, "updated": 0}}],
    })
    monkeypatch.setattr("services.import_pipeline.runner.run_address_backfill", lambda *_a, **_k: {"checked": 1, "updated": 1, "errors": 0})
    monkeypatch.setattr("services.import_pipeline.runner.run_image_enrich", lambda *_a, **_k: {"scanned_places": 1, "created": 0, "failed": 0})
    monkeypatch.setattr("services.import_pipeline.runner.normalize_places_categories", lambda *_a, **_k: {"scanned": 1, "updated": 0})
    monkeypatch.setattr("services.import_pipeline.runner.compute_city_readiness", lambda *_a, **_k: {"readiness_score": 0.9})
    monkeypatch.setattr("services.import_pipeline.runner.send_admin_alert", lambda **_k: {"sent": True})
    monkeypatch.setattr("services.import_pipeline.runner._try_refresh_snapshot", lambda *_a, **_k: None)

    run_enrichment_pipeline(db_session, job=job, city=city, actor_id="qa", notify_completion=False)
    db_session.refresh(job)

    assert not (job.status == "running" and job.finished_at is not None)
    assert job.finished_at is None

    city2 = city_factory(slug="no-running-with-finished-at-enrichment-only")
    place_factory(city_id=city2.id, slug="invariant-place-enrichment-only", title="Invariant Place Enrichment Only", category="park")
    job2 = _claimed_job(db_session, city_id=city2.id, source=service.SOURCE_ENRICHMENT_ONLY)

    monkeypatch.setattr("services.import_pipeline.enrichment_only.run_address_backfill", lambda *_a, **_k: {"checked": 1, "updated": 1, "errors": 0, "last_scanned_place_id": 0})
    monkeypatch.setattr("services.import_pipeline.enrichment_only.run_image_enrich", lambda *_a, **_k: {"scanned_places": 1, "created": 0, "errors": [], "last_scanned_place_id": 0})
    monkeypatch.setattr("services.import_pipeline.enrichment_only.run_quality_cleanup", lambda *_a, **_k: {"updated": 1})
    monkeypatch.setattr("services.import_pipeline.enrichment_only.normalize_city_categories", lambda *_a, **_k: {"scanned": 1, "updated": 0})
    monkeypatch.setattr("services.import_pipeline.enrichment_only.compute_city_readiness", lambda *_a, **_k: {"readiness_score": 0.9})
    monkeypatch.setattr("services.import_pipeline.enrichment_only.send_admin_alert", lambda **_k: {"sent": True})

    run_enrichment_only_pipeline(db_session, job=job2, city=city2, actor_id="qa")
    db_session.refresh(job2)

    assert not (job2.status == "running" and job2.finished_at is not None)
    assert job2.finished_at is None
