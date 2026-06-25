from models.city_admin_import_job import CityAdminImportJob
from models.import_job_step import ImportJobStep
from models.place_field_confidence import PlaceFieldConfidence
from models.place_photo_candidate import PlacePhotoCandidate
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.import_pipeline_foundation import run_foundation_pipeline


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="queued", source="admin_city_enrichment")
    db.add(job)
    db.commit()
    return job


def _trusted(place, *, source: str = "osm") -> None:
    place.source = source
    place.confidence = 0.9


def test_pipeline_creates_job_steps_confidence_observations_and_review_items(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-city")
    place = place_factory(city_id=city.id, slug="pipeline-park", title="Park", category="park", address=None)
    _trusted(place)
    job = _job(db_session, city.id)

    counters = run_foundation_pipeline(db_session, city=city, job=job, actor="qa")

    assert counters["found"] == 1
    assert db_session.query(ImportJobStep).filter_by(job_id=job.id, status="success").count() == 8
    assert db_session.query(SourceObservation).filter_by(city_id=city.id, canonical_place_id=place.id).count() >= 1
    assert db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id).count() >= 6
    assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, status="open").count() >= 1


def test_repeated_pipeline_run_does_not_duplicate_core_candidates(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-repeat")
    place = place_factory(city_id=city.id, slug="repeat-cafe", title="Cafe", category="coffee", address=None)
    place.image_url = "https://example.test/cafe.jpg"
    _trusted(place)
    db_session.commit()

    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    assert db_session.query(SourceObservation).filter_by(city_id=city.id, canonical_place_id=place.id).count() >= 1
    assert db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).count() == 1
    assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="address").count() == 1


def test_manual_verified_description_is_not_overwritten(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-manual")
    place = place_factory(city_id=city.id, slug="manual-place", title="Manual", category="park")
    _trusted(place)
    db_session.add(PlaceFieldConfidence(place_id=place.id, field_name="description", confidence=1.0,
                                        confidence_level="high", source_type="human_verified",
                                        is_manual_verified=True))
    db_session.commit()

    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    db_session.refresh(place)
    assert place.short_description is None


def test_ai_description_is_not_mocked_or_high_confidence(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-ai")
    place = place_factory(city_id=city.id, slug="ai-place", title="AI Place", category="park")
    _trusted(place)

    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
    confidence = db_session.query(PlaceFieldConfidence).filter_by(place_id=place.id, field_name="description").first()
    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="description").one()

    assert place.short_description is None
    assert confidence is None or confidence.confidence < 0.8
    assert review.reason == "low_confidence"


def test_category_fallback_photo_cannot_be_primary(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-photo")
    place = place_factory(city_id=city.id, slug="photo-place", title="Photo", category="park")
    place.image_url = "https://example.test/fallback.jpg"
    _trusted(place, source="category_fallback")
    db_session.commit()

    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")
    candidate = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).one()

    assert candidate.match_type == "category_fallback"
    assert candidate.is_primary_candidate is False
