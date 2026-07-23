"""Regression for the false-success publication defect found in
independent audit: services/publication_reconciliation_service.py's three
private transition helpers (_restore_published_place_flags, _hide_place,
_restore_place_from_snapshot) previously caught InvalidPublicationTransition
and silently returned None, while their callers (apply_publication_
reconciliation, rollback_publication_reconciliation) unconditionally
incremented changed_places/restored and wrote an audit log claiming a
successful change regardless of whether the transition actually applied.

These tests prove: a failed transition never increments changed_places/
restored, never writes a misleading audit entry, is reported truthfully via
the new failed_transitions counter, and successful transitions still behave
exactly as before."""

from __future__ import annotations

from models.admin_audit_log import AdminAuditLog
from models.place import Place
from services.publication_reconciliation_service import (
    RECONCILIATION_ACTION,
    apply_publication_reconciliation,
    rollback_publication_reconciliation,
)


def _leaked_public_place(city_id: int, slug: str) -> Place:
    return Place(
        city_id=city_id,
        slug=slug,
        title=slug,
        category="cafe",
        canonical_category="cafe",
        source="test",
        status="active",
        address="Test street 1",
        short_description="Description",
        lat=47.2,
        lng=39.7,
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_searchable=True,
        is_route_eligible=True,
        publication_status="published",
    )


def test_apply_reconciliation_failed_transition_does_not_increment_changed_places_new(
    db_session, city_factory, monkeypatch
) -> None:
    """Force _hide_place's transition_place_publication call to raise
    InvalidPublicationTransition and prove: changed_places stays 0,
    failed_transitions reports the failure, no audit row is written, and
    the place's public flags remain untouched."""
    import services.publication_reconciliation_service as reconciliation_module

    legacy_city = city_factory(slug="failure-legacy", name="Legacy", is_active=False, launch_status="unpublished")
    place = _leaked_public_place(legacy_city.id, "failure-legacy-place")
    db_session.add(place)
    db_session.commit()
    place_id = place.id

    def _raise(*args, **kwargs):
        raise reconciliation_module.InvalidPublicationTransition("simulated transition failure")

    monkeypatch.setattr(reconciliation_module, "transition_place_publication", _raise)

    result = apply_publication_reconciliation(
        db_session, actor="test-admin", allow_destructive=True, reason="force failure path",
    )

    assert result["changed_places"] == 0
    assert result["failed_transitions"] == 1
    assert result["audit_ids"] == []

    audit_count = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == RECONCILIATION_ACTION, AdminAuditLog.entity_id == str(place_id))
        .count()
    )
    assert audit_count == 0

    db_session.refresh(place)
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.publication_status == "published"


def test_apply_reconciliation_successful_transition_still_behaves_as_before_new(
    db_session, city_factory
) -> None:
    legacy_city = city_factory(slug="success-legacy", name="Legacy", is_active=False, launch_status="unpublished")
    place = _leaked_public_place(legacy_city.id, "success-legacy-place")
    db_session.add(place)
    db_session.commit()

    result = apply_publication_reconciliation(
        db_session, actor="test-admin", allow_destructive=True, reason="normal destructive hide",
    )

    assert result["changed_places"] == 1
    assert result["failed_transitions"] == 0
    assert len(result["audit_ids"]) == 1
    db_session.refresh(place)
    assert place.is_published is False

    audit_count = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == RECONCILIATION_ACTION, AdminAuditLog.entity_id == str(place.id))
        .count()
    )
    assert audit_count == 1


def test_rollback_reconciliation_failed_transition_does_not_increment_restored_new(
    db_session, city_factory, monkeypatch
) -> None:
    """Perform a real successful destructive hide (to get a genuine audit
    row to roll back), then force the rollback's own transition attempt to
    fail and prove restored_places stays 0, failed_transitions reports the
    failure, no rollback audit row is written, and the place is left as
    the (hidden) state the failed rollback attempt found it in."""
    import services.publication_reconciliation_service as reconciliation_module

    legacy_city = city_factory(slug="rollback-legacy", name="Legacy", is_active=False, launch_status="unpublished")
    place = _leaked_public_place(legacy_city.id, "rollback-legacy-place")
    db_session.add(place)
    db_session.commit()

    hide_result = apply_publication_reconciliation(
        db_session, actor="test-admin", allow_destructive=True, reason="setup for rollback failure test",
    )
    assert hide_result["changed_places"] == 1
    db_session.refresh(place)
    assert place.is_published is False

    def _raise(*args, **kwargs):
        raise reconciliation_module.InvalidPublicationTransition("simulated rollback failure")

    monkeypatch.setattr(reconciliation_module, "transition_place_publication", _raise)

    rollback_result = rollback_publication_reconciliation(
        db_session,
        audit_ids=hide_result["audit_ids"],
        actor="test-admin",
        reason="attempt rollback that will fail",
    )

    assert rollback_result["restored_places"] == 0
    assert rollback_result["failed_transitions"] == 1

    rollback_audit_count = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "rollback_publication_reconciliation", AdminAuditLog.entity_id == str(place.id))
        .count()
    )
    assert rollback_audit_count == 0

    db_session.refresh(place)
    # Still hidden -- the failed rollback attempt did not restore it, and
    # did not leave any other partial mutation either.
    assert place.is_published is False


def test_rollback_reconciliation_successful_transition_still_behaves_as_before_new(
    db_session, city_factory
) -> None:
    legacy_city = city_factory(slug="rollback-success-legacy", name="Legacy", is_active=False, launch_status="unpublished")
    place = _leaked_public_place(legacy_city.id, "rollback-success-legacy-place")
    db_session.add(place)
    db_session.commit()

    hide_result = apply_publication_reconciliation(
        db_session, actor="test-admin", allow_destructive=True, reason="setup for successful rollback test",
    )
    assert hide_result["changed_places"] == 1

    rollback_result = rollback_publication_reconciliation(
        db_session,
        audit_ids=hide_result["audit_ids"],
        actor="test-admin",
        reason="successful rollback",
    )

    assert rollback_result["restored_places"] == 1
    assert rollback_result["failed_transitions"] == 0
    db_session.refresh(place)
    assert place.is_published is True
