from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from models.review_queue_item import ReviewQueueItem
from services.place_change_review_service import (
    approve_place_change_review,
    reject_place_change_review,
)


def _hidden_changed_place(city_id: int) -> Place:
    return Place(
        city_id=city_id,
        slug="rostov-museum",
        title="Новое название",
        category="museum",
        lat=47.2357,
        lng=39.7015,
        status="needs_review",
        is_active=True,
        is_published=False,
        is_visible_in_catalog=False,
        is_searchable=False,
        is_route_eligible=False,
        publication_status="needs_review",
        publication_reason_code="needs_manual_review",
        publication_reason_details={"seed": True},
    )


def test_approve_place_change_blocks_publish_when_place_now_fails_hard_gates(db_session, city_factory) -> None:
    city = city_factory(slug="rostov-stale-gate", name="Ростов", is_active=True, launch_status="published")
    place = _hidden_changed_place(city.id)
    place.is_duplicate_suspected = True
    db_session.add(place)
    db_session.flush()
    review = _review_item(city.id, place.id)
    db_session.add(review)
    db_session.commit()

    result = approve_place_change_review(db_session, review.id, actor="admin")

    assert result is not None
    assert result["status"] == "resolved"
    assert place.is_published is False
    assert place.publication_status == "needs_review"
    assert place.publication_reason_code == "policy_gate_failed"
    assert "duplicate_suspected" in result["blocked_by_publication_gate"]
    transition = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert transition.to_status == "needs_review"
    assert transition.reason_code == "policy_gate_failed"
    assert transition.source == "place_change_review"


def _review_item(city_id: int, place_id: int) -> ReviewQueueItem:
    return ReviewQueueItem(
        city_id=city_id,
        place_id=place_id,
        field_name="place_change",
        reason="source_data_changed",
        severity="medium",
        status="open",
        payload={
            "kind": "place_change",
            "decision": "needs_review",
            "before_public": {
                "was_public": True,
                "status": "active",
                "is_active": True,
                "is_published": True,
                "is_visible_in_catalog": True,
                "is_searchable": True,
                "is_route_eligible": True,
                "publication_status": "published",
            },
            "changes": {
                "title": {"before": "Старое название", "after": "Новое название"},
            },
        },
    )


def test_approve_place_change_publishes_new_values_for_a_published_city(db_session, city_factory) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place = _hidden_changed_place(city.id)
    db_session.add(place)
    db_session.flush()
    review = _review_item(city.id, place.id)
    db_session.add(review)
    db_session.commit()

    result = approve_place_change_review(db_session, review.id, actor="admin")

    assert result is not None
    assert result["status"] == "resolved"
    assert place.title == "Новое название"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.publication_status == "published"
    assert place.publication_reason_code is None
    assert review.resolution == "approved"
    transition = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert transition.to_status == "published"
    assert transition.reason_code == "published"
    assert transition.source == "place_change_review"


def test_reject_place_change_restores_previous_values_and_visibility(db_session, city_factory) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    place = _hidden_changed_place(city.id)
    db_session.add(place)
    db_session.flush()
    review = _review_item(city.id, place.id)
    db_session.add(review)
    db_session.commit()

    result = reject_place_change_review(db_session, review.id, actor="admin", reason="source is incorrect")

    assert result is not None
    assert result["status"] == "resolved"
    assert place.title == "Старое название"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.publication_status == "published"
    assert place.publication_reason_code is None
    assert review.resolution == "rejected"
    transition = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert transition.to_status == "published"
    assert transition.reason_code == "published"
    assert transition.source == "place_change_review_restore"
