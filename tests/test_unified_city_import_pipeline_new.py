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

    def fake_collection(db, *, job, city, actor_id, force):
        calls.append("collection")
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


def test_enrichment_queue_alias_uses_full_import_source_new(db_session, city_factory) -> None:
    city = city_factory(slug="unified-alias")

    job = service.queue_city_enrichment_job(db_session, city_id=city.id, actor_id="qa")

    assert job.status == "queued"
    assert job.source == service.SOURCE_FULL_IMPORT
