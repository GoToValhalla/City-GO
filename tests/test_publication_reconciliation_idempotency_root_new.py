from __future__ import annotations

from models.place_publication_transition import PlacePublicationTransition
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_publication_reconciliation import reconcile_published_place


def _transition_count(db_session, place_id: int) -> int:
    return db_session.query(PlacePublicationTransition).filter(
        PlacePublicationTransition.place_id == place_id
    ).count()


def test_reconciliation_noop_preserves_comment_and_ledger(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="reconcile-noop", category="museum")
    apply_admin_city_publication_place(
        db_session,
        place,
        actor="setup",
        source="test_setup",
        reason="Original approval",
    )
    place.publication_comment = "Original approval"
    db_session.commit()
    before_count = _transition_count(db_session, place.id)

    outcome = reconcile_published_place(
        db_session,
        place,
        actor="test",
        source="test_reconcile",
        reason="Routine re-evaluation",
    )
    db_session.commit()
    db_session.refresh(place)

    assert outcome == "unchanged"
    assert _transition_count(db_session, place.id) == before_count
    assert place.publication_comment == "Original approval"


def test_reconciliation_repairs_route_state_once_without_overwriting_comment(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="reconcile-route-repair", category="museum")
    apply_admin_city_publication_place(
        db_session,
        place,
        actor="setup",
        source="test_setup",
        reason="Original approval",
    )
    place.publication_comment = "Original approval"
    place.is_route_eligible = False
    place.route_exclusion_reason = "stale_test_state"
    db_session.commit()
    before_count = _transition_count(db_session, place.id)

    first = reconcile_published_place(
        db_session,
        place,
        actor="test",
        source="test_reconcile",
        reason="Repair route state",
    )
    second = reconcile_published_place(
        db_session,
        place,
        actor="test",
        source="test_reconcile",
        reason="Repeat route state check",
    )
    db_session.commit()
    db_session.refresh(place)

    assert first == "reconciled_published"
    assert second == "unchanged"
    assert _transition_count(db_session, place.id) == before_count + 1
    assert place.publication_comment == "Original approval"
