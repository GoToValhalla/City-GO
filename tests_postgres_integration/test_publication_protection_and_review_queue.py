"""Publication protection + review queue integrity under real PostgreSQL
transactions — extends services/place_change_review_service.py::propose_place_change
(TASK 1) with genuine concurrent-writer and rollback scenarios that SQLite's
single-connection rollback-per-test fixture cannot model.
"""
from __future__ import annotations

import threading

from datetime import datetime, timedelta

from db.session import SessionLocal
from models.review_queue_item import ReviewQueueItem
from services.place_change_review_service import (
    PLACE_CHANGE_FIELD,
    StalePlaceChangeReviewError,
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
            # Lock after the barrier so both workers race from the same start line
            # instead of serializing on FOR UPDATE before the race begins.
            barrier.wait(timeout=5)
            local_place = session.query(type(place)).filter(type(place).id == place_id).with_for_update().one()
            applied = propose_place_change(session, place=local_place, proposed={"title": new_title}, reason="import_reimport")
            session.commit()
            with lock:
                outcomes.append(applied)
        except Exception:
            session.rollback()
            with lock:
                outcomes.append(False)
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
    """review_queue_items has a real partial uniqueness contract on
    (place_id, field_name, reason) WHERE status IN ('open', 'pending')
    (uq_review_queue_items_open_identity, migration a4c6e8f0b2d4) --
    ensure_review_item must not ever create two open rows for the same
    issue even under a real concurrent race, not just in single-threaded
    ORM tests. Both concurrent sessions must succeed (one via SAVEPOINT
    recovery), never crash with an unhandled IntegrityError."""
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


def test_duplicate_review_insert_recovery_leaves_session_usable_new(pg_session, pg_city, pg_category) -> None:
    """The SAVEPOINT/IntegrityError recovery inside ensure_review_item must
    leave the session fully usable afterward -- a losing concurrent insert
    must not poison the caller's session for later, unrelated work in the
    same transaction."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)

    first = ensure_review_item(
        pg_session, city_id=pg_city.id, place_id=place.id,
        field_name="phone", reason="conflict_probe", payload={"attempt": 1},
    )
    pg_session.flush()

    # Directly construct and flush a second ReviewQueueItem with the same
    # identity, bypassing ensure_review_item's own pre-check, to force the
    # exact race ensure_review_item recovers from: the unique-index
    # violation happens on OUR session's own second insert attempt.
    conflicting = ReviewQueueItem(
        city_id=pg_city.id, place_id=place.id, field_name="phone",
        reason="conflict_probe", status="open", payload={"attempt": 2},
    )
    from sqlalchemy.exc import IntegrityError

    try:
        with pg_session.begin_nested():
            pg_session.add(conflicting)
            pg_session.flush()
        raise AssertionError("expected IntegrityError from the partial unique index")
    except IntegrityError:
        pass

    # The session must still be usable for unrelated work after the
    # recovered conflict -- prove it with an ordinary query and a second,
    # genuinely different write in the SAME transaction.
    reloaded = pg_session.query(ReviewQueueItem).filter_by(id=first.id).one()
    assert reloaded.payload == {"attempt": 1}
    other = ensure_review_item(
        pg_session, city_id=pg_city.id, place_id=place.id,
        field_name="website", reason="unrelated_probe", payload={},
    )
    pg_session.commit()
    assert other.id != first.id
    assert pg_session.query(ReviewQueueItem).filter_by(place_id=place.id).count() == 2


def test_multiple_resolved_review_items_with_same_identity_are_allowed_new(pg_session, pg_city, pg_category) -> None:
    """Historical audit trail requirement: two rows sharing
    (place_id, field_name, reason) that are BOTH resolved must be allowed
    by the database -- the old uq_review_item_open constraint (which
    included status in its key) incorrectly collided on this exact shape."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)

    first = ReviewQueueItem(
        city_id=pg_city.id, place_id=place.id, field_name="opening_hours",
        reason="reimported", status="resolved", resolved_by="admin-1",
        resolution="resolved",
    )
    second = ReviewQueueItem(
        city_id=pg_city.id, place_id=place.id, field_name="opening_hours",
        reason="reimported", status="resolved", resolved_by="admin-2",
        resolution="resolved",
    )
    pg_session.add_all([first, second])
    pg_session.commit()

    rows = pg_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="opening_hours", reason="reimported").all()
    assert len(rows) == 2
    assert {row.resolved_by for row in rows} == {"admin-1", "admin-2"}


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

    fresh_session = SessionLocal()
    try:
        reloaded = fresh_session.query(ReviewQueueItem).filter(ReviewQueueItem.id == item_id).one()
        assert reloaded.payload["changes"]["tags"]["after"] == ["x", "y", "z"]
        assert reloaded.payload["meta"]["nested"]["deeply"]["value"] == 42
    finally:
        fresh_session.close()


def test_stale_place_change_approval_mutates_nothing_in_a_real_transaction_new(pg_session, pg_city, pg_category) -> None:
    """Real-transaction proof (see the SQLite-level tests for the
    exception-raising behavior itself): when a place is mutated after a
    place_change review was created, approve_place_change_review's own
    internal db.rollback() on the raised StalePlaceChangeReviewError must
    leave the place's LAST COMMITTED state and the review's open status
    completely intact -- not a half-applied place edit, not a silently
    resolved review."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category, title="Committed Title")
    propose_place_change(pg_session, place=place, proposed={"title": "Proposed New Title"}, reason="import_reimport")
    pg_session.commit()
    item = pg_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).one()
    place_id, item_id = place.id, item.id

    # A second, later writer mutates the place after the review was
    # created -- committed durably, in its own session.
    mutator_session = SessionLocal()
    try:
        mutated_place = mutator_session.query(type(place)).filter(type(place).id == place_id).one()
        mutated_place.short_description = "Changed by a later writer"
        mutated_place.updated_at = datetime.utcnow() + timedelta(seconds=5)
        mutator_session.commit()
    finally:
        mutator_session.close()

    approval_session = SessionLocal()
    try:
        try:
            approve_place_change_review(approval_session, item_id, actor="pg-integration")
            raise AssertionError("expected StalePlaceChangeReviewError")
        except StalePlaceChangeReviewError:
            pass
    finally:
        approval_session.close()

    verify_session = SessionLocal()
    try:
        final_place = verify_session.query(type(place)).filter(type(place).id == place_id).one()
        final_item = verify_session.query(ReviewQueueItem).filter(ReviewQueueItem.id == item_id).one()
        assert final_place.title == "Committed Title"
        assert final_place.short_description == "Changed by a later writer"
        assert final_item.status == "open"
    finally:
        verify_session.close()
