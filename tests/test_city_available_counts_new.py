from __future__ import annotations

from services.city_service import get_available_cities


def test_available_city_count_uses_catalog_not_route_gate_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="catalog-count-city", name="Catalog Count City")

    place_factory(slug="count-cafe", city_id=city.id, category="cafe")
    place_factory(slug="count-health", city_id=city.id, category="health")
    place_factory(slug="count-useful", city_id=city.id, category="useful")
    place_factory(slug="count-draft", city_id=city.id, category="museum", is_published=False, is_visible_in_catalog=False)

    cities = get_available_cities(db_session)
    payload = next(item for item in cities if item["slug"] == city.slug)

    assert payload["places_count"] == 3
