"""Package 3: nearest-city + start-point resolution public gates."""

from __future__ import annotations


def test_nearest_city_ignores_preview_and_unpublished_new(client, city_factory):
    city_factory(
        slug="p3-near-preview",
        name="Preview",
        launch_status="preview",
        center_lat=54.90,
        center_lng=20.40,
    )
    published = city_factory(
        slug="p3-near-pub",
        name="Published",
        launch_status="published",
        center_lat=55.00,
        center_lng=20.50,
    )

    response = client.get("/nearby/nearest-city", params={"lat": 54.90, "lng": 20.40})
    assert response.status_code == 200
    assert response.json()["city_slug"] == published.slug


def test_resolve_start_rejects_unpublished_city_and_place_new(
    client, db_session, city_factory, place_factory
):
    preview = city_factory(slug="p3-start-preview", launch_status="preview")
    city = city_factory(slug="p3-start-pub", launch_status="published")
    hidden = place_factory(
        city_id=city.id,
        slug="p3-start-hidden",
        title="Hidden Start",
        category="cafe",
        is_published=False,
        is_visible_in_catalog=False,
        publication_status="draft",
    )

    assert (
        client.post(
            "/geo/resolve-start",
            json={"city_slug": preview.slug, "type": "city_center"},
        ).status_code
        == 404
    )
    hidden_resolve = client.post(
        "/geo/resolve-start",
        json={"city_slug": city.slug, "type": "catalog_place", "place_id": hidden.id},
    )
    assert hidden_resolve.status_code == 200
    # Fail-closed: unpublished catalog place falls back to city center, not place coords.
    assert hidden_resolve.json()["type"] == "city_center"
