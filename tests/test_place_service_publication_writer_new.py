from __future__ import annotations

from models.place_publication_transition import PlacePublicationTransition
from schemas.place import PlaceCreate, PlaceUpdate
from services.place_service import create_place, update_place


def _payload(city_id: int, *, slug: str, title: str = "Тестовое место") -> dict[str, object]:
    return {
        "city_id": city_id,
        "slug": slug,
        "title": title,
        "lat": 54.9,
        "lng": 20.3,
        "category": "museum",
    }


def test_generic_create_ignores_requested_publication_and_uses_writer(db_session, city_factory) -> None:
    city = city_factory(slug="place-service-create")
    payload = PlaceCreate(
        **_payload(city.id, slug="created-place"),
        is_published=True,
        is_visible_in_catalog=True,
        is_searchable=True,
        is_route_eligible=True,
        publication_status="published",
    )

    place = create_place(db_session, payload)

    assert place.publication_status == "draft"
    assert place.publication_reason_code == "admin_create_draft"
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert place.is_route_eligible is False
    transition = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert transition.from_status == "draft"
    assert transition.to_status == "draft"
    assert transition.reason_code == "admin_create_draft"
    assert transition.source == "place_create"


def test_generic_update_cannot_change_publication_fields(
    db_session,
    city_factory,
    published_place_factory,
) -> None:
    city = city_factory(slug="place-service-update")
    place = published_place_factory(city_id=city.id, slug="published-place")
    before_transition_count = db_session.query(PlacePublicationTransition).count()

    update = PlaceUpdate(
        city_id=city.id,
        slug=place.slug,
        title="Новое название",
        lat=place.lat,
        lng=place.lng,
        category=place.category,
        is_published=False,
        is_visible_in_catalog=False,
        is_searchable=False,
        is_route_eligible=False,
        publication_status="unpublished",
    )
    updated = update_place(db_session, place.id, update)

    assert updated is not None
    assert updated.title == "Новое название"
    assert updated.publication_status == "published"
    assert updated.publication_reason_code is None
    assert updated.is_published is True
    assert updated.is_visible_in_catalog is True
    assert updated.is_searchable is True
    assert db_session.query(PlacePublicationTransition).count() == before_transition_count
