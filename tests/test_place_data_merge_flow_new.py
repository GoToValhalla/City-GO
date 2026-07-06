from __future__ import annotations

from datetime import datetime, timezone

import pytest

from models.admin_audit_log import AdminAuditLog
from models.data_foundation import EnrichmentTask
from models.place_merge_review import PlaceManualOverride, ReviewItem
from services.place_data_merge_service import PlaceDataMergeService
from services.place_merge_errors import PlaceMergeError


def test_merge_safe_auto_apply_empty_fields_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address=None)
    result = PlaceDataMergeService().apply_safe(db_session, place.id, {"address": "ул. Мира, 1"}, "EXTERNAL_API_ENRICHED", 0.9, "bot")
    db_session.refresh(place)
    assert result["status"] == "applied"
    assert place.address == "ул. Мира, 1"
    assert place.version == 2


def test_merge_creates_review_for_manual_override_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address=None)
    db_session.add(PlaceManualOverride(place_id=place.id, field_name="short_description", override_value={"value": "ручное"}, set_by="admin"))
    db_session.commit()
    result = PlaceDataMergeService().apply_safe(db_session, place.id, {"description": "новое"}, "EXTERNAL_API_ENRICHED", 0.9, "bot")
    assert result["status"] == "review_required"
    assert db_session.query(ReviewItem).filter_by(place_id=place.id, status="pending").count() == 1


def test_merge_creates_review_for_low_confidence_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address=None)
    result = PlaceDataMergeService().apply_safe(db_session, place.id, {"address": "ул. 2"}, "EXTERNAL_API_ENRICHED", 0.3, "bot")
    assert result["status"] == "review_required"
    assert "LOW_CONFIDENCE_SCORE" in db_session.get(ReviewItem, result["review_id"]).reason


def test_merge_source_priority_skip_or_review_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="ручной адрес")
    place.lineage = {"address": {"source": "MANUAL", "updated_at": datetime.now(timezone.utc).isoformat(), "confidence": 1.0, "priority": 100}}
    db_session.commit()
    result = PlaceDataMergeService().apply_safe(db_session, place.id, {"address": "адрес api"}, "OSM_INGESTION", 0.9, "bot")
    assert result["status"] == "review_required"
    assert "SOURCE_PRIORITY_LOWER" in db_session.get(ReviewItem, result["review_id"]).reason


def test_optimistic_locking_409_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый")
    item = PlaceDataMergeService().create_review_item(db_session, place, {"address": "новый"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")
    place.version += 1
    db_session.commit()
    with pytest.raises(PlaceMergeError) as exc:
        PlaceDataMergeService().apply_review_item(db_session, item.id, ["address"], "admin", item.place_version_at_creation)
    assert exc.value.code == "VERSION_MISMATCH"


def test_review_item_selective_merge_and_reject_new(db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый")
    item = PlaceDataMergeService().create_review_item(db_session, place, {"address": "новый"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")
    PlaceDataMergeService().apply_review_item(db_session, item.id, ["address"], "admin", item.place_version_at_creation)
    db_session.refresh(place)
    assert place.address == "новый"
    rejected = PlaceDataMergeService().create_review_item(db_session, place, {"address": "другой"}, "EXTERNAL_API_ENRICHED", 0.9, "VALUE_CONFLICT", None, "bot")
    PlaceDataMergeService().reject_review_item(db_session, rejected.id, "admin", "Не подходит")
    assert db_session.get(ReviewItem, rejected.id).status == "rejected"


def test_merge_updates_audit_and_enrichment_public_flow_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address=None)
    task = EnrichmentTask(place_id=place.id, city_id=place.city_id, task_type="mock", status="completed", payload={"changes": {"address": "ул. Новая, 5"}, "source": "EXTERNAL_API_ENRICHED", "confidence": 0.9})
    db_session.add(task)
    db_session.commit()
    PlaceDataMergeService().merge_from_enrichment_task(db_session, task.id)
    assert db_session.query(AdminAuditLog).filter_by(entity_id=str(place.id), action="merge_auto_apply").count() == 1
    assert client.get(f"/places/{place.id}").json()["address"] == "ул. Новая, 5"


def test_review_conflict_flow_to_public_place_after_admin_merge_new(client, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum", title="Музей", address="старый адрес")
    result = PlaceDataMergeService().apply_safe(db_session, place.id, {"address": "новый адрес"}, "EXTERNAL_API_ENRICHED", 0.9, "bot")
    item = db_session.get(ReviewItem, result["review_id"])
    PlaceDataMergeService().apply_review_item(db_session, item.id, ["address"], "admin", item.place_version_at_creation)
    assert client.get(f"/places/{place.id}").json()["address"] == "новый адрес"
