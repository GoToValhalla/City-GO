from models.place import Place
from services.place_service import get_place_by_id, get_places


def _public_place(city_id: int, slug: str) -> Place:
    return Place(
        city_id=city_id,
        slug=slug,
        title=slug,
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


def test_public_catalog_excludes_places_from_unpublished_city(db_session, city_factory) -> None:
    published_city = city_factory(slug="rostov", name="Ростов", is_active=True, launch_status="published")
    hidden_city = city_factory(slug="astrakhan", name="Астрахань", is_active=False, launch_status="unpublished")
    visible_place = _public_place(published_city.id, "visible-place")
    hidden_place = _public_place(hidden_city.id, "hidden-place")
    db_session.add_all([visible_place, hidden_place])
    db_session.commit()

    result = get_places(db_session, public_only=True)

    assert [place.id for place in result] == [visible_place.id]
    assert get_place_by_id(db_session, hidden_place.id, public_only=True) is None
