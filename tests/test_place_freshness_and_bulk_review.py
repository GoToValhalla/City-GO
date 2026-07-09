from datetime import datetime, timedelta

from models.data_foundation import PlaceFieldProvenance
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from services.place_change_review_service import bulk_resolve_place_change_reviews
from services.place_freshness_service import enqueue_stale_place_fields


def _changed_place(city_id: int, slug: str) -> Place:
    return Place(
        city_id=city_id,
        slug=slug,
        title="Новое название",
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


def _review(city_id: int, place_id: int) -> ReviewQueueItem:
    return ReviewQueueItem(
        city_id=city_id,
        place_id=place_id,
        field_name="place_change",
        reason="source_data_changed",
        severity="medium",
        status="open",
        payload={
            "decision": "needs_review",
            "before_public": {
                "status": "active",
                "is_active": True,
                "is_published": True,
                "is_visible_in_catalog": True,
                "is_searchable": True,
                "is_route_eligible": True,
                "publication_status": "published",
            },
            "changes": {"title": {"before": "Старое название", "after": "Новое название"}},
        },
    )


def test_bulk_reject_change_reviews_restores_every_selected_place(db_session, city_factory) -> None:
    city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    places = [_changed_place(city.id, f"rostov-place-{index}") for index in range(2)]
    db_session.add_all(places)
    db_session.flush()
    reviews = [_review(city.id, place.id) for place in places]
    db_session.add_all(reviews)
    db_session.commit()

    resolved, missing = bulk_resolve_place_change_reviews(
        db_session,
        [review.id for review in reviews],
        action="reject",
        actor="admin",
    )

    assert missing == []
    assert len(resolved) == 2
    assert [place.title for place in places] == ["Старое название", "Старое название"]
    assert all(place.is_published for place in places)
    assert all(review.resolution == "rejected" for review in reviews)


def test_bulk_approve_reports_per_place_gate_failure_without_hiding_it(db_session, city_factory) -> None:
    """Bulk approve must not report a uniform success: a place that currently
    fails the publication hard gates (e.g. flagged duplicate since the review
    was queued) must be visibly blocked in its own result entry, while an
    unrelated healthy place in the same batch still publishes normally."""

    city = city_factory(slug="rostov-bulk-gate", name="Ростов", is_active=True, launch_status="published")
    healthy_place = _changed_place(city.id, "rostov-bulk-healthy")
    healthy_place.category = "museum"
    blocked_place = _changed_place(city.id, "rostov-bulk-blocked")
    blocked_place.category = "museum"
    blocked_place.is_duplicate_suspected = True
    db_session.add_all([healthy_place, blocked_place])
    db_session.flush()
    reviews = [_review(city.id, healthy_place.id), _review(city.id, blocked_place.id)]
    db_session.add_all(reviews)
    db_session.commit()

    resolved, missing = bulk_resolve_place_change_reviews(
        db_session,
        [review.id for review in reviews],
        action="approve",
        actor="admin",
    )

    assert missing == []
    assert len(resolved) == 2
    by_place_id = {item["place_id"]: item for item in resolved}
    assert healthy_place.is_published is True
    assert blocked_place.is_published is False
    assert by_place_id[healthy_place.id]["blocked_by_publication_gate"] == []
    assert "duplicate_suspected" in by_place_id[blocked_place.id]["blocked_by_publication_gate"]


def test_stale_critical_fields_are_queued_with_provenance(db_session, place_factory) -> None:
    place = place_factory(title="Кафе", category="cafe")
    place.phone = "+70000000000"
    db_session.add(
        PlaceFieldProvenance(
            place_id=place.id,
            field_name="phone",
            source="osm",
            source_url="https://www.openstreetmap.org/node/1",
            obtained_at=datetime.utcnow() - timedelta(days=91),
            expires_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    db_session.commit()

    summary = enqueue_stale_place_fields(db_session)

    queued = (
        db_session.query(ReviewQueueItem)
        .filter_by(place_id=place.id, field_name="field_freshness", status="open")
        .one()
    )
    assert summary["queued_places"] == 1
    assert place.critical_field_expired is True
    assert queued.payload["fields"][0]["field"] == "phone"
    assert queued.payload["fields"][0]["source"] == "osm"
