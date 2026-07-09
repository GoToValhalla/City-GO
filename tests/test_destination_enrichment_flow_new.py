from __future__ import annotations

from models.data_foundation import EnrichmentTask
from models.place import Place
from models.place_merge_review import PlaceManualOverride, ReviewItem
from services.place_data_merge_service import PlaceDataMergeService
from tests.destination_pipeline_helpers import destination_with_scope


def test_destination_enrichment_applies_missing_fields_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="enrich-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "full"})
    place = db_session.query(Place).filter(Place.slug == "enrich-dest-core-cafe").one()
    assert place.address
    assert place.short_description
    assert place.opening_hours


def test_manual_protected_field_creates_review_item_new(client, db_session, city_factory, place_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="protected-dest")
    place = place_factory(city_id=dest.legacy_city_id, slug="protected-place", title="Protected", address=None)
    from services.destination_membership_service import upsert_membership
    upsert_membership(db_session, place_id=place.id, destination_id=dest.id, assignment_type="manual")
    db_session.add(PlaceManualOverride(place_id=place.id, field_name="address", is_protected=True, override_value={"value": None}))
    db_session.commit()
    task = EnrichmentTask(
        city_id=place.city_id,
        place_id=place.id,
        task_type="destination_deterministic_enrichment",
        status="completed",
        payload={"changes": {"address": "Ленина, 1"}, "source": "EXTERNAL_API_ENRICHED", "confidence": 0.82},
    )
    db_session.add(task)
    db_session.commit()

    result = PlaceDataMergeService().merge_from_enrichment_task(db_session, task.id, actor="test")

    assert result["status"] == "review_required"
    review = db_session.query(ReviewItem).filter_by(place_id=place.id, status="pending").one()
    assert review.reason == "MANUAL_OVERRIDE_PROTECTED"
    assert review.proposed_diff["address"]["proposed"] == "Ленина, 1"
