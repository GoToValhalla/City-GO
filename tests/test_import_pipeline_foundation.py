import allure
import pytest

from models.city_admin_import_job import CityAdminImportJob
from models.import_job_step import ImportJobStep
from models.place_field_confidence import PlaceFieldConfidence
from models.place_photo_candidate import PlacePhotoCandidate
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.import_pipeline_foundation import run_foundation_pipeline
from tests.allure_support import attach_json, given, scenario, then, when

pytestmark = [pytest.mark.import_pipeline, pytest.mark.integration, pytest.mark.regression]


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="queued", source="admin_city_enrichment")
    db.add(job)
    db.commit()
    return job


def _trusted(place, *, source: str = "osm") -> None:
    place.source = source
    place.confidence = 0.9


@scenario(
    "Импорт создаёт шаги, наблюдения, confidence и очередь проверки",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Полный foundation pipeline для нового места",
    severity=allure.severity_level.CRITICAL,
)
def test_pipeline_creates_job_steps_confidence_observations_and_review_items(db_session, city_factory, place_factory) -> None:
    with given("создан город и доверенное место без адреса"):
        city = city_factory(slug="pipeline-city")
        place = place_factory(city_id=city.id, slug="pipeline-park", title="Park", category="park", address=None)
        _trusted(place)
        job = _job(db_session, city.id)
        attach_json("Входные данные", {"city": city.slug, "place": place.slug, "job_id": job.id})

    with when("foundation pipeline обрабатывает место"):
        counters = run_foundation_pipeline(db_session, city=city, job=job, actor="qa")
        attach_json("Счётчики pipeline", counters)

    with then("все восемь шагов завершаются успешно"):
        assert counters["found"] == 1
        assert db_session.query(ImportJobStep).filter_by(job_id=job.id, status="success").count() == 8

    with then("для места создаются наблюдения и confidence"):
        assert db_session.query(SourceObservation).filter_by(city_id=city.id, canonical_place_id=place.id).count() >= 1
        assert db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id).count() >= 6

    with then("неполные данные попадают в открытую очередь проверки"):
        assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, status="open").count() >= 1


@scenario(
    "Повторный импорт не создаёт дубли служебных сущностей",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Идемпотентный повторный запуск pipeline",
    severity=allure.severity_level.CRITICAL,
)
def test_repeated_pipeline_run_does_not_duplicate_core_candidates(db_session, city_factory, place_factory) -> None:
    with given("создано место с фотографией и отсутствующим адресом"):
        city = city_factory(slug="pipeline-repeat")
        place = place_factory(city_id=city.id, slug="repeat-cafe", title="Cafe", category="coffee", address=None)
        place.image_url = "https://example.test/cafe.jpg"
        _trusted(place)
        db_session.commit()

    with when("pipeline запускается дважды для одного места"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    with then("фотокандидат и проблема адреса остаются в единственном экземпляре"):
        photo_count = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).count()
        address_issue_count = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="address").count()
        attach_json("Итоговые количества", {"photo_candidates": photo_count, "address_issues": address_issue_count})
        assert photo_count == 1
        assert address_issue_count == 1


@scenario(
    "Проверенное вручную описание не перезаписывается",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Защита ручных данных от автоматического enrichment",
    severity=allure.severity_level.CRITICAL,
)
def test_manual_verified_description_is_not_overwritten(db_session, city_factory, place_factory) -> None:
    with given("для места установлена ручная high-confidence блокировка описания"):
        city = city_factory(slug="pipeline-manual")
        place = place_factory(city_id=city.id, slug="manual-place", title="Manual", category="park")
        _trusted(place)
        db_session.add(PlaceFieldConfidence(place_id=place.id, field_name="description", confidence=1.0,
                                            confidence_level="high", source_type="human_verified",
                                            is_manual_verified=True))
        db_session.commit()

    with when("pipeline пытается дополнить описание"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        db_session.refresh(place)

    with then("автоматический черновик не изменяет защищённое поле"):
        assert place.short_description is None


@scenario(
    "Автоматическое описание сохраняется как проверяемый черновик",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Генерация описания с контролем происхождения",
    severity=allure.severity_level.CRITICAL,
)
def test_generated_description_is_reviewable_and_not_high_confidence(db_session, city_factory, place_factory) -> None:
    with given("создано доверенное место без описания"):
        city = city_factory(slug="pipeline-description-draft")
        place = place_factory(city_id=city.id, slug="description-draft-place", title="Городской парк", category="park")
        _trusted(place)

    with when("pipeline формирует описание из подтверждённых полей"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        confidence = db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id, field_name="description").one()
        reviews = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="description", status="open").all()
        attach_json("Результат описания", {
            "description": place.short_description,
            "confidence": confidence.confidence,
            "source_type": confidence.source_type,
            "review_reasons": [item.reason for item in reviews],
        })

    with then("черновик содержит название места и не получает high confidence"):
        assert place.short_description
        assert "Городской парк" in place.short_description
        assert confidence.confidence < 0.8

    with then("происхождение черновика сохранено и создана одна задача проверки"):
        assert confidence.source_type == "citygo_description_draft"
        assert len(reviews) == 1
        assert reviews[0].reason == "generated_description_review"


@scenario(
    "Категорийная заглушка фотографии не становится основной",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Безопасная обработка фотокандидатов",
)
def test_category_fallback_photo_cannot_be_primary(db_session, city_factory, place_factory) -> None:
    with given("место использует категорийную заглушку изображения"):
        city = city_factory(slug="pipeline-photo")
        place = place_factory(city_id=city.id, slug="photo-place", title="Photo", category="park")
        place.image_url = "https://example.test/fallback.jpg"
        _trusted(place, source="category_fallback")
        db_session.commit()

    with when("pipeline создаёт фотокандидата"):
        run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
        candidate = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).one()

    with then("кандидат помечен как fallback и не выбран основным"):
        assert candidate.match_type == "category_fallback"
        assert candidate.is_primary_candidate is False
