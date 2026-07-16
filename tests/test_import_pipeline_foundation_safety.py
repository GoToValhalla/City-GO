from datetime import datetime, time
from zoneinfo import ZoneInfo

import allure
import pytest

from models.city_admin_import_job import CityAdminImportJob
from models.place_field_confidence import PlaceFieldConfidence
from models.place_schedule import PlaceSchedule
from services.import_pipeline_foundation import run_foundation_pipeline
from services.open_now_service import get_open_now_places, get_weekday_code
from tests.allure_support import attach_json, given, scenario, then, when

pytestmark = [pytest.mark.import_pipeline, pytest.mark.integration, pytest.mark.regression]


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="queued", source="admin_city_enrichment")
    db.add(job)
    db.commit()
    return job


def _trusted(place) -> None:
    place.source = "osm"
    place.confidence = 0.9


@scenario("Инфраструктурные категории не попадают в прогулочные маршруты", epic="Платформа данных", feature="Политика публикации и маршрутов", story="Ограничение route eligibility по категории", severity=allure.severity_level.CRITICAL)
def test_pharmacies_and_services_are_not_route_eligible(db_session, city_factory, place_factory) -> None:
    with given("в городе созданы медицинские, сервисные и транспортные места"):
        city = city_factory(slug="pipeline-service")
        places = [
            place_factory(city_id=city.id, slug="health", title="Health", category="health"),
            place_factory(city_id=city.id, slug="pharmacy", title="Pharmacy", category="pharmacy"),
            place_factory(city_id=city.id, slug="service", title="Service", category="service"),
            place_factory(city_id=city.id, slug="stop", title="Stop", category="bus_stop"),
        ]
        for place in places:
            _trusted(place)
    with when("pipeline рассчитывает публикацию и route eligibility"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        attach_json("Решения по местам", [{"slug": item.slug, "route": item.is_route_eligible, "status": item.publication_status} for item in places])
    with then("ни одна инфраструктурная точка не разрешена для обычного маршрута"):
        assert all(item.is_route_eligible is False for item in places)
        assert places[1].publication_status == "needs_review"


@scenario("Место с координатами 0,0 архивируется", epic="Платформа данных", feature="Контроль качества координат", story="Блокировка невалидной географии", severity=allure.severity_level.BLOCKER)
def test_invalid_coordinates_are_archived(db_session, city_factory, place_factory) -> None:
    with given("создано место с координатами 0,0"):
        city = city_factory(slug="pipeline-invalid-coords")
        place = place_factory(city_id=city.id, slug="bad-coords", title="Bad", category="park", lat=0.0, lng=0.0)
        _trusted(place)
    with when("pipeline применяет publication gate"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        db_session.refresh(place)
    with then("место скрыто из каталога и маршрутов"):
        assert place.publication_status == "archived"
        assert place.is_active is False
        assert place.is_route_eligible is False


@scenario("Конфликтное устаревшее расписание не считается признаком открытия", epic="Каталог мест", feature="Открыто сейчас", story="Безопасная обработка недостоверных часов работы", severity=allure.severity_level.CRITICAL)
def test_low_conflict_stale_opening_hours_are_not_open_now(db_session, city_factory, place_factory) -> None:
    with given("место имеет расписание с low confidence, stale и conflict"):
        city = city_factory(slug="pipeline-open-now", timezone="UTC")
        place = place_factory(city_id=city.id, slug="open-place", title="Open", category="coffee")
        weekday = get_weekday_code(datetime.now(ZoneInfo("UTC")))
        db_session.add(PlaceSchedule(place_id=place.id, weekday=weekday, open_time=time(0, 0), close_time=time(23, 59)))
        db_session.add(PlaceFieldConfidence(place_id=place.id, field_name="opening_hours", confidence=0.2, confidence_level="low", source_type="import", freshness_status="stale", conflict_status="conflict"))
        db_session.commit()
    with when("сервис запрашивает открытые сейчас места"):
        result = get_open_now_places(db_session, city.slug)
        attach_json("Результат Open Now", [item.id for item in result])
    with then("недостоверное место не попадает в выдачу"):
        assert result == []


@scenario("Сбой необязательного шага переводит импорт в partial success", epic="Платформа данных", feature="Надёжность import pipeline", story="Изоляция сбоя необязательного шага", severity=allure.severity_level.CRITICAL)
def test_failed_non_critical_step_marks_partial_success(db_session, city_factory, place_factory, monkeypatch) -> None:
    with given("генератор описания недоступен"):
        city = city_factory(slug="pipeline-partial")
        place = place_factory(city_id=city.id, slug="partial-place", title="Partial", category="park")
        _trusted(place)
        def _boom(*_args, **_kwargs):
            raise RuntimeError("ai worker down")
        monkeypatch.setattr("services.import_pipeline_foundation_steps._description_draft", _boom)
        job = _job(db_session, city.id)
    with when("pipeline продолжает работу после сбоя необязательного шага"):
        counters = run_foundation_pipeline(db_session, city=city, job=job, actor="qa")
        # run_foundation_pipeline никогда не пишет job.status напрямую —
        # исход фазы возвращается через job.step_details["source_enrichment_status"],
        # а терминализацию родительского job делает только вызывающий код
        # (см. admin_city_import_job_service._transition).
        attach_json("Статус операции", {"status": job.step_details.get("source_enrichment_status"), "counters": counters})
    with then("job завершается partial_success и фиксирует один сбой"):
        assert job.step_details["source_enrichment_status"] == "partial_success"
        assert counters["failed"] == 1
        assert job.step_details["pipeline_counters"]["failed"] == 1


@scenario("Сбой критического шага останавливает импорт", epic="Платформа данных", feature="Надёжность import pipeline", story="Остановка операции при потере исходных данных", severity=allure.severity_level.BLOCKER)
def test_critical_step_failure_marks_job_failed(db_session, city_factory, place_factory, monkeypatch) -> None:
    with given("критический шаг сбора исходных данных завершается ошибкой"):
        city = city_factory(slug="pipeline-critical")
        place = place_factory(city_id=city.id, slug="critical-place", title="Critical", category="park")
        _trusted(place)
        def _boom(*_args, **_kwargs):
            raise RuntimeError("source unavailable")
        monkeypatch.setattr("services.import_pipeline_foundation_steps._observe_place", _boom)
        job = _job(db_session, city.id)
    with when("pipeline запускает критический шаг"):
        with pytest.raises(RuntimeError, match="source unavailable"):
            run_foundation_pipeline(db_session, city=city, job=job, actor="qa")
    with then("job получает failed и сохраняет понятную причину"):
        # run_foundation_pipeline никогда не пишет job.status напрямую —
        # исход фазы возвращается через job.step_details["source_enrichment_status"].
        assert job.step_details["source_enrichment_status"] == "failed"
        assert job.last_error == "source unavailable"
