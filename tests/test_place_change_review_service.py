from models.place import Place
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
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_searchable=False,
        is_route_eligible=False,
        publication_status="needs_review",
    )


def test_approve_place_change_blocks_publish_when_place_now_fails_hard_gates(db_session, city_factory) -> None:
    """A review item's stored decision reflects the place's state when the change
    was first queued. If a later data-quality scan flags the place (e.g. as a
    suspected duplicate) before an admin approves it, approval must not publish
    a place that would currently fail the publication hard gates."""

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
    assert "duplicate_suspected" in result["blocked_by_publication_gate"]


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
    assert review.resolution == "approved"


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
    assert review.resolution == "rejected"
