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
