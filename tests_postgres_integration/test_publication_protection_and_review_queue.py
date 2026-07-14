"""Publication protection + review queue integrity under real PostgreSQL
transactions — extends services/place_change_review_service.py::propose_place_change
(TASK 1) with genuine concurrent-writer and rollback scenarios that SQLite's
single-connection rollback-per-test fixture cannot model.
"""
from __future__ import annotations

import threading

from db.session import SessionLocal
from models.review_queue_item import ReviewQueueItem
from services.place_change_review_service import (
    PLACE_CHANGE_FIELD,
    approve_place_change_review,
    propose_place_change,
    reject_place_change_review,
)
from services.review_queue_service import ensure_review_item

from conftest import make_published_place


def test_two_concurrent_proposals_on_same_published_place_never_double_apply_new(pg_session, pg_city, pg_category) -> None:
    """Two 'import workers' proposing conflicting changes to the same
    published place at the same time must never both write to the live
    row — the place stays published with its original content until an
    admin resolves exactly one candidate."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category, title="Original Title")
    place_id = place.id

    barrier = threading.Barrier(2)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def propose(new_title: str) -> None:
        session = SessionLocal()
        try:
            local_place = session.query(type(place)).filter(type(place).id == place_id).with_for_update().one()
            barrier.wait(timeout=5)
            applied = propose_place_change(session, place=local_place, proposed={"title": new_title}, reason="import_reimport")
            session.commit()
            with lock:
                outcomes.append(applied)
        finally:
            session.close()

    threads = [threading.Thread(target=propose, args=(f"Racing Title {i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(applied is False for applied in outcomes)

    pg_session.refresh(place)
    assert place.title == "Original Title"
    assert place.is_published is True

    items = pg_session.query(ReviewQueueItem).filter_by(place_id=place_id, field_name=PLACE_CHANGE_FIELD, status="open").all()
    assert len(items) == 1


def test_review_queue_open_item_uniqueness_is_enforced_by_postgres_new(pg_session, pg_city, pg_category) -> None:
    """review_queue_items has a real uniqueness contract on
    (place_id, field_name, reason, status) — ensure_review_item must not
    ever create two open rows for the same issue even under a real
    concurrent race, not just in single-threaded ORM tests."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    place_id = place.id

    barrier = threading.Barrier(2)

    def enqueue() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            ensure_review_item(
                session,
                city_id=pg_city.id,
                place_id=place_id,
                field_name="address",
                reason="conflict",
                payload={"note": "race"},
            )
            session.commit()
        finally:
            session.close()

    threads = [threading.Thread(target=enqueue) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    open_items = pg_session.query(ReviewQueueItem).filter_by(place_id=place_id, field_name="address", reason="conflict", status="open").all()
    assert len(open_items) == 1


def test_rejected_review_keeps_public_version_across_real_transaction_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category, title="Approved Public Title")
    propose_place_change(pg_session, place=place, proposed={"title": "Attempted Overwrite"}, reason="import_reimport")
    pg_session.commit()

    item = pg_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()
    reject_place_change_review(pg_session, item.id, actor="pg-integration")
    pg_session.commit()
    pg_session.refresh(place)

    assert place.title == "Approved Public Title"
    assert place.is_published is True


def test_approved_review_applies_candidate_across_real_transaction_new(pg_session, pg_city, pg_category) -> None:
    place = make_published_place(pg_session, city=pg_city, category=pg_category, title="Old Title")
    propose_place_change(pg_session, place=place, proposed={"title": "New Approved Title"}, reason="import_reimport")
    pg_session.commit()

    item = pg_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()
    approve_place_change_review(pg_session, item.id, actor="pg-integration")
    pg_session.commit()
    pg_session.refresh(place)

    assert place.title == "New Approved Title"
    assert place.is_published is True


def test_transaction_rollback_leaves_no_partial_review_item_new(pg_session, pg_city, pg_category) -> None:
    """A crash mid-transaction after propose_place_change but before commit
    must leave neither a partially-written Place nor an orphaned
    ReviewQueueItem — real ROLLBACK, not the SQLite fixture's rollback."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category, title="Stable Title")
    session = SessionLocal()
    try:
        local_place = session.query(type(place)).filter(type(place).id == place.id).one()
        propose_place_change(session, place=local_place, proposed={"title": "Never Committed"}, reason="import_reimport")
        session.rollback()
    finally:
        session.close()

    pg_session.refresh(place)
    assert place.title == "Stable Title"
    items = pg_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).all()
    assert items == []


def test_review_queue_payload_jsonb_round_trips_nested_structures_new(pg_session, pg_city, pg_category) -> None:
    """payload is JSONB in PostgreSQL (models/review_queue_item.py) — verify
    nested dict/list structures survive a real commit + fresh read, which
    SQLite's JSON-as-text variant does not meaningfully validate."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    nested_payload = {
        "kind": "place_change",
        "applied": False,
        "changes": {
            "title": {"before": "A", "after": "B"},
            "tags": {"before": ["x", "y"], "after": ["x", "y", "z"]},
        },
        "meta": {"nested": {"deeply": {"value": 42}}},
    }
    item = ensure_review_item(
        pg_session,
        city_id=pg_city.id,
        place_id=place.id,
        field_name="jsonb_probe",
        reason="jsonb_contract",
        payload=nested_payload,
    )
    pg_session.commit()
    item_id = item.id
    pg_session.expunge_all()

    fresh_session = SessionLocal()
    try:
        reloaded = fresh_session.query(ReviewQueueItem).filter(ReviewQueueItem.id == item_id).one()
        assert reloaded.payload["changes"]["tags"]["after"] == ["x", "y", "z"]
        assert reloaded.payload["meta"]["nested"]["deeply"]["value"] == 42
    finally:
        fresh_session.close()
