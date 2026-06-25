from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from models.city_admin_import_job import CityAdminImportJob
from models.place_field_confidence import PlaceFieldConfidence
from models.place_schedule import PlaceSchedule
from services.import_pipeline_foundation import run_foundation_pipeline
from services.open_now_service import get_open_now_places, get_weekday_code


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="queued", source="admin_city_enrichment")
    db.add(job)
    db.commit()
    return job


def _trusted(place) -> None:
    place.source = "osm"
    place.confidence = 0.9


def test_pharmacies_and_services_are_not_route_eligible(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-service")
    health = place_factory(city_id=city.id, slug="health", title="Health", category="health")
    pharmacy = place_factory(city_id=city.id, slug="pharmacy", title="Pharmacy", category="pharmacy")
    service = place_factory(city_id=city.id, slug="service", title="Service", category="service")
    stop = place_factory(city_id=city.id, slug="stop", title="Stop", category="bus_stop")
    _trusted(health)
    _trusted(pharmacy)
    _trusted(service)
    _trusted(stop)
    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    assert health.is_route_eligible is False
    assert pharmacy.is_route_eligible is False
    assert service.is_route_eligible is False
    assert stop.is_route_eligible is False
    assert pharmacy.publication_status == "needs_review"


def test_invalid_coordinates_are_archived(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-invalid-coords")
    place = place_factory(city_id=city.id, slug="bad-coords", title="Bad", category="park", lat=0.0, lng=0.0)
    _trusted(place)
    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    db_session.refresh(place)
    assert place.publication_status == "archived"
    assert place.is_active is False
    assert place.is_route_eligible is False


def test_low_conflict_stale_opening_hours_are_not_open_now(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-open-now", timezone="UTC")
    place = place_factory(city_id=city.id, slug="open-place", title="Open", category="coffee")
    weekday = get_weekday_code(datetime.now(ZoneInfo("UTC")))
    db_session.add(PlaceSchedule(place_id=place.id, weekday=weekday, open_time=time(0, 0), close_time=time(23, 59)))
    db_session.add(PlaceFieldConfidence(place_id=place.id, field_name="opening_hours", confidence=0.2,
                                        confidence_level="low", source_type="import",
                                        freshness_status="stale", conflict_status="conflict"))
    db_session.commit()

    assert get_open_now_places(db_session, city.slug) == []


def test_failed_non_critical_step_marks_partial_success(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="pipeline-partial")
    place = place_factory(city_id=city.id, slug="partial-place", title="Partial", category="park")
    _trusted(place)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("ai worker down")

    monkeypatch.setattr("services.import_pipeline_foundation_steps._description_draft", _boom)
    job = _job(db_session, city.id)
    counters = run_foundation_pipeline(db_session, city=city, job=job, actor="qa")

    assert job.status == "partial_success"
    assert counters["failed"] == 1
    assert job.step_details["pipeline_counters"]["failed"] == 1


def test_critical_step_failure_marks_job_failed(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="pipeline-critical")
    place = place_factory(city_id=city.id, slug="critical-place", title="Critical", category="park")
    _trusted(place)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("source unavailable")

    monkeypatch.setattr("services.import_pipeline_foundation_steps._observe_place", _boom)
    job = _job(db_session, city.id)

    with pytest.raises(RuntimeError, match="source unavailable"):
        run_foundation_pipeline(db_session, city=city, job=job, actor="qa")

    assert job.status == "failed"
    assert job.last_error == "source unavailable"
