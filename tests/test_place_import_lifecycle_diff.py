from datetime import datetime

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.place_import_lifecycle_service import apply_accepted_import_to_place


def _place(**overrides):
    values = {
        "city_id": 1,
        "category_id": 10,
        "slug": "test-place",
        "title": "Тестовое место",
        "short_description": "Описание",
        "category": "museum",
        "address": "Улица, 1",
        "lat": 55.1,
        "lng": 37.2,
        "source": "osm",
        "source_url": "https://www.openstreetmap.org/node/1",
        "status": "active",
        "is_active": True,
        "is_published": True,
        "is_visible_in_catalog": True,
        "is_route_eligible": True,
        "is_searchable": True,
        "publication_status": "published",
        "publication_reason_code": None,
        "publication_reason_details": {},
        "average_visit_duration_minutes": 75,
        "updated_at": datetime(2026, 1, 1),
        "last_verified_at": datetime(2026, 1, 1),
    }
    values.update(overrides)
    return Place(**values)


def _item(**overrides):
    values = {
        "title": "Тестовое место",
        "short_description": "Описание",
        "category": "museum",
        "address": "Улица, 1",
        "raw_lat": 55.1,
        "raw_lng": 37.2,
        "source_url": "https://www.openstreetmap.org/node/1",
        "lifecycle_status": "active",
        "opening_hours": None,
        "website": None,
        "phone": None,
    }
    values.update(overrides)
    return values


def test_unchanged_place_is_not_touched():
    place = _place()
    old_updated_at = place.updated_at
    old_verified_at = place.last_verified_at

    decision = apply_accepted_import_to_place(place, _item(), category_id=10, visit_duration_minutes=75)

    assert decision.action == "unchanged"
    assert decision.changed_fields == []
    assert place.updated_at == old_updated_at
    assert place.last_verified_at == old_verified_at
    assert place.is_published is True
    assert place.publication_status == "published"


def test_changed_published_place_stays_public_and_unmodified_pending_review():
    place = _place()

    decision = apply_accepted_import_to_place(
        place,
        _item(address="Новая улица, 2"),
        category_id=10,
        visit_duration_minutes=75,
    )

    assert decision.action == "needs_review"
    assert "address" in decision.changed_fields
    assert decision.change_set["address"] == {"before": "Улица, 1", "after": "Новая улица, 2"}
    assert place.address == "Улица, 1"
    assert place.is_active is True
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.publication_status == "published"
    assert place.publication_reason_code is None
    assert place.unpublished_at is None


def test_changed_unpublished_place_uses_writer_and_is_sent_to_review(
    db_session,
    draft_place_factory,
) -> None:
    place = draft_place_factory(
        slug="import-lifecycle-draft",
        title="Тестовое место",
        short_description="Описание",
        category="museum",
        address="Улица, 1",
        lat=55.1,
        lng=37.2,
        source="osm",
        source_url="https://www.openstreetmap.org/node/1",
        status="active",
        average_visit_duration_minutes=75,
    )
    initial_transition_count = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .count()
    )

    decision = apply_accepted_import_to_place(
        place,
        _item(address="Новая улица, 2"),
        category_id=place.category_id,
        visit_duration_minutes=75,
    )

    assert decision.action == "needs_review"
    assert "address" in decision.changed_fields
    assert place.address == "Новая улица, 2"
    assert place.status == "needs_review"
    assert place.publication_status == "needs_review"
    assert place.publication_reason_code == "needs_manual_review"
    assert place.is_active is True
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert place.is_route_eligible is False

    transitions = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .order_by(PlacePublicationTransition.id.asc())
        .all()
    )
    assert len(transitions) == initial_transition_count + 1
    transition = transitions[-1]
    assert transition.to_status == "needs_review"
    assert transition.reason_code == "needs_manual_review"
    assert transition.source == "place_import_lifecycle"
