"""Regression for the SAVEPOINT-cleanup gap found in independent audit of
commit a79ad3a7: services/review_queue_service.py::ensure_review_item and
services/publication_policy.py::ensure_review_queue_item previously only
handled IntegrityError explicitly (manual savepoint.commit()/
savepoint.rollback() calls) -- any OTHER exception raised between the
insert and the commit could leave the raw Connection-level SAVEPOINT
neither committed nor rolled back. Both functions now use the
NestedTransaction as a context manager, which guarantees rollback for ANY
exception and commit only on success."""

from __future__ import annotations

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from models.review_queue_item import ReviewQueueItem
from services.review_queue_service import ensure_review_item


def _seed_open_item(db_session, *, place, field_name="address", reason="conflict"):
    db_session.execute(
        insert(ReviewQueueItem).values(
            city_id=place.city_id,
            place_id=place.id,
            field_name=field_name,
            reason=reason,
            status="open",
            payload={},
        )
    )
    db_session.commit()


def test_integrity_error_recovery_still_returns_the_winning_row_new(db_session, place_factory) -> None:
    """The exact scenario ensure_review_item's SAVEPOINT recovery exists
    for: a conflicting open row already exists (simulating a concurrent
    winner), and ensure_review_item must recover by returning that row
    instead of raising or fabricating a duplicate."""
    place = place_factory()
    _seed_open_item(db_session, place=place, field_name="phone", reason="conflict_probe")

    result = ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="phone",
        reason="conflict_probe",
        payload={"attempt": "second"},
    )

    assert result.status == "open"
    assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="phone", reason="conflict_probe").count() == 1


def test_non_integrity_error_rolls_back_savepoint_and_propagates_new(db_session, place_factory, monkeypatch) -> None:
    """Simulate a non-IntegrityError failure (e.g. a driver-level error
    unrelated to the unique constraint) occurring inside the SAVEPOINT
    block. The context-manager form must still roll back the SAVEPOINT
    (proven directly via NestedTransaction.is_active, the mechanism-level
    fact that distinguishes this from the old manual try/except
    IntegrityError pattern -- a RuntimeError falls through that except
    clause untouched, leaving the SAVEPOINT's is_active True/dangling
    under the old code, but False/sealed under the context-manager
    rewrite) and let the exception propagate -- not swallow it, not
    leave a dangling transaction state that poisons the session for
    later use."""
    place = place_factory()

    from sqlalchemy.engine import Connection

    original_begin_nested = Connection.begin_nested
    captured: dict[str, object] = {}

    def spying_begin_nested(self):
        savepoint = original_begin_nested(self)
        captured["savepoint"] = savepoint
        return savepoint

    original_execute = Connection.execute

    def failing_execute(self, statement, *args, **kwargs):
        if isinstance(statement, insert(ReviewQueueItem).__class__) and "review_queue_items" in str(statement):
            raise RuntimeError("simulated non-IntegrityError failure")
        return original_execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "begin_nested", spying_begin_nested)
    monkeypatch.setattr(Connection, "execute", failing_execute)

    with pytest.raises(RuntimeError, match="simulated non-IntegrityError failure"):
        ensure_review_item(
            db_session,
            city_id=place.city_id,
            place_id=place.id,
            field_name="website",
            reason="non_integrity_probe",
            payload={},
        )

    monkeypatch.undo()

    assert "savepoint" in captured, "ensure_review_item must open a SAVEPOINT even on the failing path"
    assert captured["savepoint"].is_active is False, (
        "the SAVEPOINT must be rolled back (is_active=False) after a "
        "non-IntegrityError exception -- a dangling active SAVEPOINT "
        "here means the exception fell through unhandled cleanup"
    )

    # The session must remain fully usable afterward -- no row was left
    # half-inserted, and an unrelated query/write still works.
    assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="website").count() == 0
    other = ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="opening_hours",
        reason="unrelated_probe",
        payload={},
    )
    assert other.field_name == "opening_hours"


def test_unrelated_pending_orm_state_is_not_flushed_by_the_savepoint_new(db_session, place_factory) -> None:
    """The bug this whole rewrite exists to fix: entering a SAVEPOINT via
    the ORM Session's own begin_nested() unconditionally flushes the
    ENTIRE pending unit of work, which previously persisted an unrelated,
    still-in-progress Place mutation to the database prematurely. Using
    the raw Connection for the SAVEPOINT (as both ensure_review_item and
    ensure_review_queue_item now do) must NOT flush place's pending,
    uncommitted short_description change."""
    place = place_factory()
    place.short_description = "still being edited, not yet flushed"

    ensure_review_item(
        db_session,
        city_id=place.city_id,
        place_id=place.id,
        field_name="description",
        reason="unrelated_pending_state_probe",
        payload={},
    )

    # Read the raw committed DB value directly, bypassing the ORM identity
    # map, to prove the pending change was never flushed by the SAVEPOINT.
    from sqlalchemy import text

    raw_value = db_session.execute(
        text("SELECT short_description FROM places WHERE id = :id"), {"id": place.id}
    ).scalar()
    assert raw_value is None, (
        "ensure_review_item's SAVEPOINT must not flush unrelated pending "
        f"ORM state, but place.short_description was persisted as {raw_value!r}"
    )

    # The pending change is still there in memory, and a real flush/commit
    # by the caller (not ensure_review_item) still applies it normally.
    assert place.short_description == "still being edited, not yet flushed"
    db_session.commit()
    db_session.refresh(place)
    assert place.short_description == "still being edited, not yet flushed"
