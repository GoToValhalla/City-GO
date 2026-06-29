from models.review_queue_item import ReviewQueueItem
from services.review_queue_service import ensure_review_item


def test_ensure_review_item_reuses_exact_open_reason(db_session, place_factory):
    place = place_factory(title="Место с часами")
    generic = ReviewQueueItem(
        city_id=place.city_id,
        place_id=place.id,
        field_name="opening_hours",
        reason="low_confidence",
        status="open",
        severity="medium",
        payload={},
    )
    exact = ReviewQueueItem(
        city_id=place.city_id,
        place_id=place.id,
        field_name="opening_hours",
        reason="missing_after_enrichment",
        status="open",
        severity="medium",
        payload={},
    )
    db_session.add_all([generic, exact])
    db_session.commit()

    item = ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="opening_hours",
        reason="missing_after_enrichment",
        severity="low",
        payload={"source": "foundation"},
    )
    db_session.commit()

    assert item.id == exact.id
    rows = (
        db_session.query(ReviewQueueItem)
        .filter_by(place_id=place.id, field_name="opening_hours", status="open")
        .order_by(ReviewQueueItem.id.asc())
        .all()
    )
    assert [row.reason for row in rows] == ["low_confidence", "missing_after_enrichment"]
    assert rows[1].severity == "low"
    assert rows[1].payload == {"source": "foundation"}


def test_ensure_review_item_creates_single_pending_item_for_same_reason(db_session, place_factory):
    place = place_factory(title="Место без фото")

    first = ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="image_url",
        reason="missing_after_enrichment",
        severity="medium",
    )
    second = ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="image_url",
        reason="missing_after_enrichment",
        severity="high",
    )
    db_session.commit()

    assert second is first
    rows = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="image_url", status="open").all()
    assert len(rows) == 1
    assert rows[0].reason == "missing_after_enrichment"
    assert rows[0].severity == "high"
