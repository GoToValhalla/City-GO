from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.base import Base
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from scripts.auto_process_publication_backlog import process_backlog
from scripts.repair_publication_states import apply_plan, build_plan
from services.admin_city_import_job_service import _refresh_snapshot_light
from tests.allure_support import title


@title("Failed import snapshot сохраняет published city product state")
def test_failed_import_snapshot_does_not_unpublish_published_city(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="failed-import-city", name="Failed Import", is_active=True, launch_status="published")
    published_place_factory(city_id=city.id, slug="failed-import-published")
    job = CityAdminImportJob(city_id=city.id, status="failed", source="admin_city_import", last_error="boom")
    db_session.add(job)
    db_session.commit()

    _refresh_snapshot_light(db_session, city=city, job=job, source="failed_import_test")
    db_session.refresh(city)
    db_session.refresh(job)

    assert city.is_active is True
    assert city.launch_status == "published"
    assert job.status == "failed"
    assert job.step_details["data_coverage"]["places_published"] == 1


@title("Partial import snapshot сохраняет published city product state")
def test_partial_import_snapshot_does_not_unpublish_published_city(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="partial-import-city", name="Partial Import", is_active=True, launch_status="published")
    published_place_factory(city_id=city.id, slug="partial-import-published")
    job = CityAdminImportJob(city_id=city.id, status="partial_success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    _refresh_snapshot_light(db_session, city=city, job=job, source="partial_import_test")
    db_session.refresh(city)
    db_session.refresh(job)

    assert city.is_active is True
    assert city.launch_status == "published"
    assert job.status == "partial_success"
    assert job.step_details["data_coverage"]["places_published"] == 1


@title("Repair dry-run build_plan не пишет изменения в DB")
def test_repair_publication_states_build_plan_is_dry_run(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="repair-dry-run-city", name="Repair Dry Run", is_active=False, launch_status="draft")
    published_place_factory(city_id=city.id, slug="repair-published-place")

    plan = build_plan(db_session, city_slug=city.slug, restore_cities=True, repair_place_flags=False, limit=None)
    db_session.refresh(city)

    assert len(plan["city_changes"]) == 1
    assert city.is_active is False
    assert city.launch_status == "draft"


@title("Repair apply восстанавливает published city с опубликованными местами")
def test_repair_publication_states_apply_restores_city(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="repair-apply-city", name="Repair Apply", is_active=False, launch_status="draft")
    published_place_factory(city_id=city.id, slug="repair-apply-place")

    plan = build_plan(db_session, city_slug=city.slug, restore_cities=True, repair_place_flags=False, limit=None)
    apply_plan(db_session, plan)
    db_session.refresh(city)

    assert city.is_active is True
    assert city.launch_status == "published"


@title("Auto backlog processor reports cursor-safe counters in dry-run")
def test_auto_process_publication_backlog_reports_expected_counters(tmp_path, monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    import scripts.auto_process_publication_backlog as backlog_script

    monkeypatch.setattr(backlog_script, "SessionLocal", TestingSessionLocal)
    with TestingSessionLocal() as db:
        city = City(slug="backlog-script-city", name="Backlog Script", is_active=True, launch_status="published")
        db.add(city)
        db.flush()
        db.add_all(
            [
                Place(slug="missing-address", title="Missing Address", city_id=city.id, category="museum", lat=1.0, lng=1.0, publication_status="auto_backlog", is_active=True, is_published=False, is_visible_in_catalog=False, is_searchable=False, is_route_eligible=False),
                Place(slug="missing-photo", title="Missing Photo", city_id=city.id, category="museum", lat=1.0, lng=1.0, address="ул. Фото, 1", publication_status="auto_backlog", is_active=True, is_published=False, is_visible_in_catalog=False, is_searchable=False, is_route_eligible=False),
                Place(slug="duplicate-backlog", title="Duplicate", city_id=city.id, category="museum", lat=1.0, lng=1.0, address="ул. Дубль, 1", image_url="https://img.test/a.jpg", publication_status="auto_backlog", is_duplicate_suspected=True, is_active=True, is_published=False, is_visible_in_catalog=False, is_searchable=False, is_route_eligible=False),
            ]
        )
        db.commit()

    result = process_backlog(city_slug="backlog-script-city", limit=10)

    assert result["checked"] == 3
    assert result["missing_address"] == 1
    assert result["missing_photo"] == 1
    assert result["duplicate_suspected"] == 1


@title("Import/enrichment snapshot не снимает published place с публикации")
def test_import_snapshot_does_not_unpublish_published_place(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="published-place-stable", name="Published Place Stable")
    place = published_place_factory(city_id=city.id, slug="stable-published-place", category="museum")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_snapshot_refresh")
    db_session.add(job)
    db_session.commit()

    _refresh_snapshot_light(db_session, city=city, job=job, source="enrichment_snapshot_test")
    db_session.refresh(place)

    assert place.is_active is True
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True
    assert place.publication_status == "published"
