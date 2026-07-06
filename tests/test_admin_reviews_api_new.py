from __future__ import annotations

from models.place_merge_review import ReviewItem
from services.place_data_merge_service import PlaceDataMergeService

AUTH = {"Authorization": "Bearer test"}


def test_admin_reviews_list_and_diff_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый")
    item = PlaceDataMergeService().create_review_item(db_session, place, {"address": "новый"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")

    listing = client.get("/admin/reviews", headers=AUTH)
    diff = client.get(f"/admin/reviews/{item.id}/diff", headers=AUTH)

    assert listing.status_code == 200
    assert listing.json()[0]["place_name"] == "Музей"
    assert diff.status_code == 200
    assert diff.json()["proposed_diff"]["address"]["proposed"] == "новый"


def test_admin_review_merge_and_reject_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый")
    item = PlaceDataMergeService().create_review_item(db_session, place, {"address": "новый"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")

    merged = client.post(f"/admin/reviews/{item.id}/merge", headers=AUTH, json={"fields_to_apply": ["address"], "expected_version": item.place_version_at_creation})

    assert merged.status_code == 200
    assert merged.json()["status"] == "approved"
    db_session.refresh(place)
    assert place.address == "новый"


def test_admin_review_merge_version_conflict_returns_409_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый")
    item = PlaceDataMergeService().create_review_item(db_session, place, {"address": "новый"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")
    place.version += 1
    db_session.commit()

    response = client.post(f"/admin/reviews/{item.id}/merge", headers=AUTH, json={"fields_to_apply": ["address"], "expected_version": item.place_version_at_creation})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "VERSION_MISMATCH"


def test_admin_manual_override_and_trigger_enrich_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address=None)
    override = client.post(f"/admin/places/{place.id}/manual-override", headers=AUTH, json={"field_name": "short_description", "override_value": "ручное"})
    trigger = client.post(f"/admin/places/{place.id}/trigger-enrich", headers=AUTH, json={"changes": {"description": "новое"}, "confidence": 0.9})

    assert override.status_code == 200
    assert trigger.status_code == 200
    assert trigger.json()["status"] == "review_required"
    assert db_session.query(ReviewItem).filter_by(place_id=place.id, status="pending").count() == 1
