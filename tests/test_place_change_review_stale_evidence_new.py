"""services/place_change_review_service.py must not apply a place-change
review's stored before/after values if the place has been mutated since
the review was created -- approve/reject must reject with a specific
conflict and leave both the place and the review untouched."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from models.place import Place
from services.place_change_review_service import (
    StalePlaceChangeReviewError,
    approve_place_change_review,
    propose_place_change,
    reject_place_change_review,
)
from models.review_queue_item import ReviewQueueItem


def _published_place(city_id: int, **overrides) -> Place:
    base = dict(
        city_id=city_id,
        slug="stale-evidence-place",
        title="Старое название",
        category="museum",
        lat=47.2357,
        lng=39.7015,
        status="active",
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_searchable=True,
        is_route_eligible=True,
        publication_status="published",
    )
    base.update(overrides)
    return Place(**base)


def test_propose_place_change_stores_updated_at_evidence_marker_new(db_session, city_factory) -> None:
    city = city_factory(slug="stale-evidence-city", name="Ростов", is_active=True, launch_status="published")
    place = _published_place(city.id)
    db_session.add(place)
    db_session.commit()

    propose_place_change(db_session, place=place, proposed={"title": "Новое название"}, reason="import_reimport")
    db_session.commit()

    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="place_change").one()
    assert review.payload["place_updated_at_creation"] is not None
    assert datetime.fromisoformat(review.payload["place_updated_at_creation"]) == place.updated_at


def test_approve_rejects_stale_review_new(db_session, city_factory) -> None:
    """approve_place_change_review must reject a stale review instead of
    applying its payload's before/after values -- see the companion
    real-transaction proof in tests_postgres_integration/
    test_publication_protection_and_review_queue.py for confirmation that
    neither the place nor the review is left mutated after the conflict
    (the SQLite fixture's single-connection rollback-per-test model cannot
    distinguish "this one operation rolled back" from "the whole test
    transaction rolled back", so that stronger assertion needs a real
    PostgreSQL transaction)."""
    city = city_factory(slug="stale-evidence-approve-city", name="Ростов", is_active=True, launch_status="published")
    place = _published_place(city.id)
    db_session.add(place)
    db_session.commit()

    propose_place_change(db_session, place=place, proposed={"title": "Новое название"}, reason="import_reimport")
    db_session.commit()
    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="place_change").one()

    # Simulate an unrelated mutation of the place after the review was
    # created (e.g. an admin edit, or a second, later import cycle).
    place.short_description = "Изменено другим путём"
    place.updated_at = datetime.utcnow() + timedelta(seconds=5)
    db_session.commit()

    with pytest.raises(StalePlaceChangeReviewError):
        approve_place_change_review(db_session, review.id, actor="admin")


def test_reject_rejects_stale_review_new(db_session, city_factory) -> None:
    city = city_factory(slug="stale-evidence-reject-city", name="Ростов", is_active=True, launch_status="published")
    place = _published_place(city.id)
    db_session.add(place)
    db_session.commit()

    propose_place_change(db_session, place=place, proposed={"title": "Новое название"}, reason="import_reimport")
    db_session.commit()
    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="place_change").one()

    place.short_description = "Изменено другим путём"
    place.updated_at = datetime.utcnow() + timedelta(seconds=5)
    db_session.commit()

    with pytest.raises(StalePlaceChangeReviewError):
        reject_place_change_review(db_session, review.id, actor="admin")


def test_approve_succeeds_when_place_is_unchanged_since_proposal_new(db_session, city_factory) -> None:
    """The staleness guard must not be a false-positive trap: an untouched
    place must still approve normally."""
    city = city_factory(slug="stale-evidence-fresh-city", name="Ростов", is_active=True, launch_status="published")
    place = _published_place(city.id)
    db_session.add(place)
    db_session.commit()

    propose_place_change(db_session, place=place, proposed={"title": "Новое название"}, reason="import_reimport")
    db_session.commit()
    review = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name="place_change").one()

    result = approve_place_change_review(db_session, review.id, actor="admin")

    assert result is not None
    assert result["status"] == "resolved"
    assert place.title == "Новое название"
