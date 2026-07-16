from models.city_admin_import_job import CityAdminImportJob
from models.review_queue_item import ReviewQueueItem
from services import admin_city_import_job_service as service
from services.import_pipeline_foundation import run_foundation_pipeline


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="queued", source="admin_city_enrichment")
    db.add(job)
    db.commit()
    return job


def test_publication_review_queue_is_field_level_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-review-field")
    place = place_factory(city_id=city.id, slug="review-field", title="Review", category="health")
    place.source = "osm"
    place.confidence = 0.9

    run_foundation_pipeline(db_session, city=city, job=_job(db_session, city.id), actor="qa")

    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, reason="non_tourist_category").one()
    assert item.field_name == "category"


def test_review_queue_item_requires_persisted_import_job_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """End-to-end through the real admin import job entrypoint: the job row
    must be durably created (flushed with a real id) before any review queue
    item referencing it is created, and every created review item's job_id
    must resolve to that persisted job — never an orphan/guessed id."""

    city = city_factory(slug="review-queue-job-persisted")
    place = place_factory(city_id=city.id, slug="review-queue-job-persisted-place", title="Review", category="health")
    place.source = "osm"
    place.confidence = 0.9
    queued = service.queue_city_import_job(db_session, city_id=city.id, actor_id="qa")
    db_session.commit()
    job = service.claim_queued_job(db_session, job_id=queued.id, worker_id="test-worker", actor_id="qa")

    def fake_collection(db, *, job, city, actor_id, force, notify_completion=True):
        db.commit()
        return {"import": {"places_saved": 0}, "status": "success", "changed_place_ids": [place.id]}

    monkeypatch.setattr(service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 80})

    result = service.run_city_import_job(db_session, city_id=city.id, actor_id="qa", job_id=job.id)

    assert result.id is not None
    reviews = db_session.query(ReviewQueueItem).filter_by(place_id=place.id).all()
    assert len(reviews) >= 1
    for review in reviews:
        assert review.job_id is not None
        linked_job = db_session.get(CityAdminImportJob, review.job_id)
        assert linked_job is not None
        assert linked_job.id == result.id
