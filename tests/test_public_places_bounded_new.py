"""Public places list must have a hard default/max limit, and place detail
must tolerate missing photo/address/hours without breaking the response."""

from __future__ import annotations


def test_places_list_has_default_limit_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="places-default-limit-city")
    for i in range(5):
        place_factory(city_id=city.id, slug=f"places-default-limit-place-{i}", title=f"Places Default Limit Place {i}")

    response = client.get("/places/", params={"city_slug": city.slug})

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 20


def test_places_list_rejects_limit_above_max_new(client, city_factory) -> None:
    city_factory(slug="places-max-limit-city")

    response = client.get("/places/", params={"city_slug": "places-max-limit-city", "limit": 500})

    assert response.status_code == 422


def test_place_detail_tolerates_missing_photo_address_hours_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="places-missing-fields-city")
    place = place_factory(
        city_id=city.id,
        slug="places-missing-fields-place",
        title="Places Missing Fields Place",
        image_url=None,
        address=None,
    )

    response = client.get(f"/places/{place.id}")

    assert response.status_code == 200
    body = response.json()
    assert body.get("address") is None
    assert body.get("image_url") is None


def test_places_list_empty_catalog_returns_structured_empty_response_new(client, city_factory) -> None:
    city_factory(slug="places-empty-catalog-city")

    response = client.get("/places/", params={"city_slug": "places-empty-catalog-city"})

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
