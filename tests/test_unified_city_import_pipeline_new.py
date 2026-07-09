from models.city_admin_import_job import CityAdminImportJob
from services import admin_city_import_job_service as service


def test_city_import_runs_collection_then_source_enrichment_new(
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    city = city_factory(slug="unified-pipeline")
    place_factory(city_id=city.id, slug="unified-place", title="Unified Place", category="park")
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()
    calls: list[str] = []

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        calls.append("collection")
        assert notify_completion is False
        return {"import": {"places_saved": 1}}

    def fake_source_enrichment(db, *, city, job, actor):
        calls.append("source_enrichment")
        return {"found": 1, "fields_enriched": 2, "provider_errors": 0}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 80})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

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
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        job.status = "success"
        db.commit()
        return {"import": {"places_saved": 1}}

    def fake_source_enrichment(db, *, city, job, actor):
        job.status = "failed"
        job.last_error = "critical provider setup failure"
        return {"found": 1, "failed": 1}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 0})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

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
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        job.status = "partial_success"
        job.last_error = "some import scopes failed"
        db.commit()
        return {"import": {"places_saved": 1}}

    def fake_source_enrichment(db, *, city, job, actor):
        return {"found": 1, "fields_enriched": 0, "provider_errors": 0}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 80})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

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
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    def fake_collection_raises(db, *, job, city, actor_id, force, notify_completion=True):
        raise RuntimeError("provider setup failed")

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection_raises)

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

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
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_FULL_IMPORT, current_step="queued")
    db_session.add(job)
    db_session.commit()

    dns_error = "Failed to resolve overpass-api.de: [Errno -2] Name or service not known"

    def fake_collection_all_scopes_fail(db, *, job, city, actor_id, force, notify_completion=True):
        job.status = "failed"
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
        return {"import": {"scopes_total": 3, "scopes_succeeded": 0, "last_error": job.last_error}}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection_all_scopes_fail)

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")

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
    job = CityAdminImportJob(city_id=city.id, status="queued", source=service.SOURCE_ENRICHMENT_ONLY, current_step="queued")
    db_session.add(job)
    db_session.commit()

    def fake_enrichment_only(db, *, job, city, actor_id):
        job.status = "success"
        job.step_details = {**dict(job.step_details or {}), "changed_place_ids": []}
        db.commit()

    def fake_source_enrichment(db, *, city, job, actor):
        job.status = "failed"
        job.last_error = "critical provider setup failure"
        return {"found": 1, "failed": 1}

    monkeypatch.setattr(service, "run_enrichment_only_pipeline", fake_enrichment_only)
    monkeypatch.setattr(service, "run_foundation_pipeline", fake_source_enrichment)

    result = service.run_enrichment_only_job(db_session, city_id=city.id, actor_id="qa")

    assert result.status == "failed"
