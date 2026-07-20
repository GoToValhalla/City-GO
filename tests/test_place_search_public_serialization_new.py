"""Package 3: place search uses PublicPlaceRead, not PlaceRead admin fields."""

from __future__ import annotations

ADMIN_LEAK_KEYS = {
    "publication_status",
    "is_published",
    "is_route_eligible",
    "is_visible_in_catalog",
    "internal_status",
    "verification_status",
}


def test_place_search_serializes_public_place_read_new(
    client, city_factory, published_place_factory
):
    city = city_factory(slug="p3-search-city")
    published_place_factory(
        city_id=city.id,
        slug="p3-search-cafe",
        title="Search Cafe",
        category="cafe",
    )

    response = client.get(
        "/places/search/",
        params={"q": "Search", "city_slug": city.slug},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    item = next(row for row in body["items"] if row["slug"] == "p3-search-cafe")
    assert "title" in item and "name" in item
    assert "category_info" in item
    assert "data_quality" in item
    assert ADMIN_LEAK_KEYS.isdisjoint(item.keys())
