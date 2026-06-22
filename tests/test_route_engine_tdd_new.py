"""TDD regressions for the route engine product invariants."""

from __future__ import annotations


START_REPLACED_WARNING = "start_coordinates_replaced_with_city_center"


def test_tm_007_admin_dry_run_bypasses_draft_city_status_new(client, city_factory, place_factory) -> None:
    city = city_factory(
        slug="tm-admin-draft-city",
        name="Тестовый город в импорте",
        center_lat=46.3497,
        center_lng=48.0408,
        is_active=False,
        launch_status="importing",
    )
    _seed_route_places(place_factory, city.id, 46.3497, 48.0408)

    response = client.post(
        "/admin/routes/dry-run",
        json={"city_slug": city.slug, "duration_min": 180, "interests": ["culture"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["selected_places"] > 0
    assert body["quality"]["route_status"] != "failed"


def test_tm_010_admin_dry_run_recovers_zero_zero_start_new(client, city_factory, place_factory) -> None:
    city = city_factory(
        slug="tm-zero-start",
        center_lat=43.2389,
        center_lng=76.8897,
    )
    _seed_route_places(place_factory, city.id, 43.2389, 76.8897)

    response = client.post(
        "/admin/routes/dry-run",
        json={"city_slug": city.slug, "duration_min": 120, "start_lat": 0.0, "start_lng": 0.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["selected_places"] > 0
    assert START_REPLACED_WARNING in body["request_summary"]["start_warnings"]
    assert START_REPLACED_WARNING in body["quality"]["warnings"]


def test_route_engine_does_not_select_zero_zero_place_new(client, city_factory, place_factory) -> None:
    city = city_factory(
        slug="tm-bad-place-coords",
        center_lat=54.9611,
        center_lng=20.4703,
    )
    bad = place_factory(
        slug="bad-zero-zero",
        title="Битая точка",
        category="museum",
        city_id=city.id,
        lat=0.0,
        lng=0.0,
    )
    _seed_route_places(place_factory, city.id, 54.9611, 20.4703)

    response = client.post(
        "/admin/routes/dry-run",
        json={"city_slug": city.slug, "duration_min": 180},
    )

    assert response.status_code == 200
    selected_ids = {item["place_id"] for item in response.json()["selected_places"]}
    assert selected_ids
    assert bad.id not in selected_ids


def _seed_route_places(place_factory, city_id: int, lat: float, lng: float) -> None:
    specs = [
        ("museum", "Музей", 0.0000, 0.0000),
        ("park", "Парк", 0.0020, 0.0020),
        ("landmark", "Памятник", 0.0040, 0.0010),
        ("cafe", "Кофе", 0.0010, 0.0040),
    ]
    for index, (category, title, dlat, dlng) in enumerate(specs, start=1):
        place_factory(
            slug=f"route-tdd-{city_id}-{index}",
            title=title,
            category=category,
            city_id=city_id,
            lat=lat + dlat,
            lng=lng + dlng,
            address=f"Адрес {index}",
            is_active=True,
            is_published=True,
            is_visible_in_catalog=True,
            is_route_eligible=True,
            publication_status="published",
        )
