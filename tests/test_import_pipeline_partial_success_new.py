from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.import_pipeline.runner import run_enrichment_pipeline


def test_hard_pipeline_failure_after_saved_places_becomes_partial_success_new(db_session, monkeypatch) -> None:
    city = City(name="Recovered City", slug="recovered-city", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_import")
    place = Place(city_id=city.id, slug="recovered-park", title="Recovered Park", lat=55.0, lng=37.0, category="park")
    db_session.add_all([job, place])
    db_session.commit()
    alerts: list[dict[str, object]] = []

    monkeypatch.setattr("services.import_pipeline.runner.run_osm_import_only", lambda *_args, **_kwargs: {
        "results": [{"status": "success", "scope": "tourist_core", "import_result": {"raw_count": 1, "created": 0, "updated": 0}}],
    })
    monkeypatch.setattr("services.import_pipeline.runner.run_address_backfill", lambda *_args, **_kwargs: {"checked": 1, "updated": 0, "errors": 0})
    monkeypatch.setattr("services.import_pipeline.runner.run_image_enrich", lambda *_args, **_kwargs: {"scanned_places": 1, "created": 0, "failed": 0})
    monkeypatch.setattr("services.import_pipeline.runner.normalize_city_categories", lambda *_args, **_kwargs: {"scanned": 1, "updated": 0, "skipped": 0})
    monkeypatch.setattr("services.import_pipeline.runner.run_quality_cleanup", lambda *_args, **_kwargs: {"updated": 1})
    monkeypatch.setattr("services.import_pipeline.runner.compute_city_readiness", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("readiness down")))
    monkeypatch.setattr("services.import_pipeline.runner.send_admin_alert", lambda **kwargs: alerts.append(kwargs) or {"sent": True})

    result = run_enrichment_pipeline(db_session, job=job, city=city, actor_id="test-admin")
    job_id = job.id
    city_id = city.id
    db_session.rollback()
    persisted_job = db_session.get(CityAdminImportJob, job_id)
    persisted_city = db_session.get(City, city_id)

    assert result["partial_success_after_error"]["step"] == "computing_readiness"
    assert persisted_job.status == "partial_success"
    assert persisted_job.current_step == "ready_for_review"
    assert persisted_job.last_error == "readiness down"
    assert persisted_job.step_details["partial_success_after_error"]["places_total"] == 1
    assert persisted_city.launch_status == "review_required"
    assert persisted_city.is_active is False
    assert alerts[0]["title"] == "Import completed with warnings"
    assert alerts[0]["level"] == "warning"
