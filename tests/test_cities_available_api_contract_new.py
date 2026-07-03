from __future__ import annotations

from fastapi.testclient import TestClient


def _by_slug(items: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(item["slug"]): item for item in items}


def test_cities_available_api_returns_stable_catalog_shape_new(client: TestClient, city_factory, place_factory) -> None:
    city = city_factory(slug="api-city", name="API City", region="Region", country="Country")
    place_factory(city_id=city.id, slug="api-place", title="API Place", category="museum")

    response = client.get("/cities/available")

    assert response.status_code == 200
    rows = _by_slug(response.json())
    assert rows["api-city"] == {
        "slug": "api-city",
        "name": "API City",
        "country": "Country",
        "region": "Region",
        "launch_status": "published",
        "places_count": 1,
    }


def test_cities_available_api_counter_does_not_drop_route_ineligible_catalog_places_new(
    client: TestClient,
    city_factory,
    place_factory,
) -> None:
    city = city_factory(slug="api-counter", name="API Counter")
    place_factory(city_id=city.id, slug="route-ready", title="Route Ready", category="museum", is_route_eligible=True)
    place_factory(city_id=city.id, slug="catalog-only", title="Catalog Only", category="park", is_route_eligible=False)

    response = client.get("/cities/available")

    assert response.status_code == 200
    assert _by_slug(response.json())["api-counter"]["places_count"] == 2
