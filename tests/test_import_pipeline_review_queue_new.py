from models.city_admin_import_job import CityAdminImportJob
from models.review_queue_item import ReviewQueueItem
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
