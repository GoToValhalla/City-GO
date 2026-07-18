from __future__ import annotations

import pytest

from models.place_publication_transition import PlacePublicationTransition
from services.publication_state_writer import (
    InvalidPublicationTransition,
    REASON_ADMIN_REJECT,
    REASON_ADMIN_UNPUBLISH,
    REASON_PUBLISHED,
    transition_place_publication,
)
from tests.allure_support import title


@title("Canonical writer atomically records current reason and append-only transition")
def test_unpublish_records_current_reason_and_transition(
    db_session,
    published_place_factory,
) -> None:
    place = published_place_factory(slug="reason-writer-unpublish")

    transition = transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        human_comment="Temporary operator unpublish",
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "unpublished"
    assert place.publication_reason_code == REASON_ADMIN_UNPUBLISH
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert place.is_route_eligible is False
    assert transition.id is not None
    stored = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert stored.reason_code == REASON_ADMIN_UNPUBLISH
    assert stored.from_status == "published"
    assert stored.to_status == "unpublished"


@title("Publishing clears current non-public reason but preserves transition history")
def test_publish_clears_current_reason_and_keeps_history(
    db_session,
    draft_place_factory,
) -> None:
    place = draft_place_factory(slug="reason-writer-publish")

    transition_place_publication(
        db_session,
        place,
        to_status="unpublished",
        reason_code=REASON_ADMIN_UNPUBLISH,
        actor="admin:test",
        source="admin_manual",
        lock_place=False,
    )
    transition_place_publication(
        db_session,
        place,
        to_status="published",
        reason_code=REASON_PUBLISHED,
        actor="admin:test",
        source="admin_manual",
        route_eligible_when_published=True,
        lock_place=False,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "published"
    assert place.publication_reason_code is None
    assert place.publication_reason_details == {}
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True
    transitions = (
        db_session.query(PlacePublicationTransition)
        .filter_by(place_id=place.id)
        .order_by(PlacePublicationTransition.id.asc())
        .all()
    )
    assert [item.reason_code for item in transitions] == [
        REASON_ADMIN_UNPUBLISH,
        REASON_PUBLISHED,
    ]


@title("Reason code and target status compatibility is fail-closed")
def test_writer_rejects_reason_for_wrong_target(
    db_session,
    draft_place_factory,
) -> None:
    place = draft_place_factory(slug="reason-writer-invalid")

    with pytest.raises(InvalidPublicationTransition):
        transition_place_publication(
            db_session,
            place,
            to_status="needs_review",
            reason_code=REASON_ADMIN_REJECT,
            actor="admin:test",
            source="admin_manual",
            lock_place=False,
        )

    assert db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).count() == 0
