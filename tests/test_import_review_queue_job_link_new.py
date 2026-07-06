from __future__ import annotations

from data.scripts.import_city_osm import _apply_import
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from models.import_batch import ImportBatch
from models.review_queue_item import ReviewQueueItem


def test_osm_import_review_queue_uses_city_admin_import_job_id_not_batch_id_new(db_session, city_factory, place_factory):
    city = city_factory(slug="zelenogradsk-like")
    place = place_factory(
        city_id=city.id,
        slug="zelenogradsk-like-cafe-old-cafe-osm-node-1",
        title="Old Cafe",
        category="cafe",
        address="Old address",
    )
    place.source_url = "https://www.openstreetmap.org/node/1"
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", current_step="collecting_places")
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Tourist core", bbox={"south": 54, "west": 20, "north": 55, "east": 21}, enabled=True, status="enabled", import_profile="tourist_core")
    db_session.add_all([job, scope])
    db_session.flush()
    seed_batch = ImportBatch(city_id=city.id, scope_id=scope.id, mode="apply", dry_run=False)
    db_session.add(seed_batch)
    db_session.commit()

    result = _apply_import(
        db_session,
        city,
        scope,
        "tourist_core",
        raw_objects=[],
        normalized=[_accepted_item()],
        city_admin_import_job_id=job.id,
    )

    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="place_change").one()
    assert result["needs_review"] == 1
    assert review.job_id == job.id
    assert review.payload["city_admin_import_job_id"] == job.id
    assert review.payload["import_batch_id"] != job.id


def _accepted_item() -> dict[str, object]:
    return {
        "accepted": True,
        "source_external_id": "osm:node:1",
        "source_url": "https://www.openstreetmap.org/node/1",
        "payload_hash": "hash",
        "raw_name": "New Cafe",
        "raw_category": "cafe",
        "raw_lat": 54.5,
        "raw_lng": 20.5,
        "raw_payload": {"id": 1},
        "lifecycle_status": "active",
        "slug": "zelenogradsk-like-cafe-old-cafe-osm-node-1",
        "title": "New Cafe",
        "category": "cafe",
        "address": "New address",
        "short_description": "Updated description",
        "opening_hours": {"raw": "Mo-Su 10:00-20:00"},
        "website": None,
        "phone": None,
    }
