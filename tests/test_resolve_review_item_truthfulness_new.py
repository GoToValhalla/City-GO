"""services/review_queue_service.py::resolve_review_item must be truthful,
idempotent, locked, and audited -- it performs no entity mutation and must
never claim otherwise, especially for field_name="publication" items which
have no dedicated handler that actually re-applies a publication decision."""

from __future__ import annotations

from models.admin_audit_log import AdminAuditLog
from models.review_queue_item import ReviewQueueItem
from services.review_queue_service import (
    DISPOSITION_ACKNOWLEDGED_NO_MUTATION,
    resolve_review_item,
)


def _open_item(place, **overrides) -> ReviewQueueItem:
    base = dict(
        city_id=place.city_id,
        place_id=place.id,
        field_name="opening_hours",
        reason="missing_after_enrichment",
        severity="medium",
        status="open",
        payload={},
    )
    base.update(overrides)
    return ReviewQueueItem(**base)


def test_resolve_review_item_not_found_returns_falsy_result_new(db_session) -> None:
    result = resolve_review_item(db_session, 999999, actor="admin", resolution="fixed")

    assert result.ok is False
    assert result.item is None
    assert result.already_resolved is False


def test_resolve_review_item_succeeds_from_open_state_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    item = _open_item(place)
    db_session.add(item)
    db_session.commit()

    result = resolve_review_item(db_session, item.id, actor="admin-1", resolution="fixed")
    db_session.commit()

    assert result.ok is True
    assert result.item.status == "resolved"
    assert result.item.resolved_by == "admin-1"
    assert result.item.resolution == "fixed"
    assert result.item.resolved_at is not None


def test_double_resolve_does_not_overwrite_first_resolution_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    item = _open_item(place)
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    first = resolve_review_item(db_session, item_id, actor="admin-1", resolution="fixed")
    db_session.commit()
    assert first.ok is True
    first_resolved_at = first.item.resolved_at
    first_resolved_by = first.item.resolved_by
    first_resolution = first.item.resolution

    second = resolve_review_item(db_session, item_id, actor="admin-2", resolution="different_resolution")
    db_session.commit()

    assert second.ok is False
    assert second.already_resolved is True
    assert second.item is not None
    assert second.item.id == item_id

    reloaded = db_session.query(ReviewQueueItem).filter_by(id=item_id).one()
    assert reloaded.resolved_by == first_resolved_by == "admin-1"
    assert reloaded.resolved_at == first_resolved_at
    assert reloaded.resolution == first_resolution == "fixed"


def test_resolve_review_item_writes_admin_audit_row_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    item = _open_item(place)
    db_session.add(item)
    db_session.commit()

    result = resolve_review_item(db_session, item.id, actor="admin-1", resolution="fixed")
    db_session.commit()

    assert result.ok is True
    audit = (
        db_session.query(AdminAuditLog)
        .filter_by(entity_type="review_queue_item", entity_id=str(item.id), action="resolve_review_item")
        .one()
    )
    assert audit.actor == "admin-1"
    assert audit.new_value["status"] == "resolved"
    assert audit.new_value["resolution"] == "fixed"


def test_resolve_publication_review_records_explicit_no_mutation_disposition_new(db_session, place_factory) -> None:
    """A field_name="publication" item has no handler that actually
    re-applies the publication decision -- resolving it through the
    generic endpoint must record an explicit, audited disposition that
    makes clear no publication state changed, not a resolution string
    indistinguishable from a real applied decision."""
    place = place_factory(title="Место", is_published=False, publication_status="needs_review")
    item = _open_item(
        place, field_name="publication", reason="LOW_TRUST_SCORE",
        payload={"decision": "send_to_review", "trust_score": 40},
    )
    db_session.add(item)
    db_session.commit()

    result = resolve_review_item(db_session, item.id, actor="admin-1", resolution="approved")
    db_session.commit()

    assert result.ok is True
    assert result.item.resolution == DISPOSITION_ACKNOWLEDGED_NO_MUTATION
    # The place's own publication state must be completely untouched.
    db_session.refresh(place)
    assert place.is_published is False
    assert place.publication_status == "needs_review"

    audit = (
        db_session.query(AdminAuditLog)
        .filter_by(entity_type="review_queue_item", entity_id=str(item.id), action="resolve_review_item")
        .one()
    )
    assert audit.new_value["publication_state_changed"] is False
    assert audit.new_value["requested_resolution"] == "approved"


def test_resolve_review_item_locks_row_for_update_new(db_session, place_factory, monkeypatch) -> None:
    """Confirms the resolve query actually requests a row lock -- a
    regression guard against silently dropping with_for_update() in a
    future refactor."""
    place = place_factory(title="Место")
    item = _open_item(place)
    db_session.add(item)
    db_session.commit()

    calls: list[str] = []
    from sqlalchemy.orm import Query

    original_with_for_update = Query.with_for_update

    def spy(self, *args, **kwargs):
        calls.append("with_for_update")
        return original_with_for_update(self, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", spy)

    resolve_review_item(db_session, item.id, actor="admin-1", resolution="fixed")

    assert "with_for_update" in calls
