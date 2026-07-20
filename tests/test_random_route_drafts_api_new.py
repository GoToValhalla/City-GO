import pytest


pytestmark = [pytest.mark.api, pytest.mark.routing]


def _random_payload(city_slug: str, **extra):
    payload = {
        "city_slug": city_slug,
        "budget_minutes": 120,
        "start": {"type": "city_center", "label": "Центр города"},
        "category_mode": "none",
        "selected_category_slugs": [],
        "seed": 42,
        "session_token": "test-session-token-01",
    }
    payload.update(extra)
    return payload


def _token() -> str:
    return "test-session-token-01"


def _headers() -> dict[str, str]:
    from services.route_draft_access import SESSION_HEADER

    return {SESSION_HEADER: _token()}


def test_random_route_without_categories_creates_non_empty_draft(client, city_factory, place_factory):
    city = city_factory(slug="random-city")
    place_factory(slug="random-cafe", title="Coffee", city_id=city.id, category="cafe")
    place_factory(slug="random-park", title="Park", city_id=city.id, category="park")

    response = client.post("/routes/random", json=_random_payload(city.slug))

    assert response.status_code == 200
    payload = response.json()
    assert payload["route_status"] in {"full", "partial"}
    assert len(payload["points"]) >= 2
    assert payload["category_mode"] == "none"


def test_balanced_categories_are_soft_preference_not_hard_filter(client, city_factory, place_factory):
    city = city_factory(slug="balanced-city")
    place_factory(slug="balanced-cafe", title="Cafe", city_id=city.id, category="cafe")
    place_factory(slug="balanced-park", title="Park", city_id=city.id, category="park")
    place_factory(slug="balanced-walk", title="Walk", city_id=city.id, category="walk")

    response = client.post(
        "/routes/random",
        json=_random_payload(city.slug, category_mode="balanced", selected_category_slugs=["museum"]),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["points"]) >= 2
    assert payload["category_summary"]["missing"] == ["museum"]
    assert payload["category_summary"]["neutral_added"] >= 2


def test_random_route_zero_eligible_returns_no_route_warning(client, city_factory, place_factory):
    city = city_factory(slug="empty-random")
    place_factory(slug="draft-only", city_id=city.id, is_route_eligible=False)

    response = client.post("/routes/random", json=_random_payload(city.slug))

    assert response.status_code == 200
    payload = response.json()
    assert payload["route_status"] == "no_route"
    assert payload["points"] == []
    assert payload["warnings"][0]["code"] == "NO_ELIGIBLE_PLACES"


def test_draft_remove_add_replace_and_search_alias_flow(client, city_factory, place_factory):
    city = city_factory(slug="edit-city")
    park = place_factory(slug="edit-park", title="Парк", city_id=city.id, category="park")
    place_factory(slug="edit-food", title="Еда", city_id=city.id, category="food")
    place_factory(slug="edit-walk", title="Прогулка", city_id=city.id, category="walk")
    created = client.post("/routes/random", json=_random_payload(city.slug, seed=7)).json()
    cafe = place_factory(slug="edit-cafe", title="Кофейня", city_id=city.id, category="cafe")
    museum = place_factory(slug="edit-museum", title="Музей", city_id=city.id, category="museum")

    search = client.get(
        f"/routes/drafts/{created['draft_id']}/search-places",
        params={"q": "кофе", "limit": 5},
        headers=_headers(),
    ).json()
    assert search["items"][0]["category"] == "cafe"

    first_point = created["points"][0]
    removed = client.post(
        f"/routes/drafts/{created['draft_id']}/remove-point",
        headers=_headers(),
        json={"point_id": first_point["id"], "version": created["version"]},
    ).json()
    assert removed["version"] == created["version"] + 1
    stale = client.post(
        f"/routes/drafts/{created['draft_id']}/remove-point",
        headers=_headers(),
        json={"point_id": removed["points"][0]["id"], "version": created["version"]},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_DRAFT_VERSION"

    add_response = client.post(
        f"/routes/drafts/{created['draft_id']}/add-point",
        headers=_headers(),
        json={
            "place_id": cafe.id,
            "after_position": 1,
            "version": removed["version"],
        },
    )
    assert add_response.status_code == 200
    added = add_response.json()
    replace_response = client.post(
        f"/routes/drafts/{created['draft_id']}/replace-point",
        headers=_headers(),
        json={
            "point_id": added["points"][0]["id"],
            "replacement_place_id": museum.id,
            "version": added["version"],
        },
    )
    assert replace_response.status_code == 200
    assert museum.id in [point["place_id"] for point in replace_response.json()["points"]]
    assert park.city_id == city.id


def test_city_start_points_and_out_of_city_geolocation(client, city_factory):
    city = city_factory(slug="start-city", center_lat=54.0, center_lng=20.0)

    points = client.get(f"/cities/{city.slug}/start-points")
    resolved = client.post(
        "/geo/resolve-start",
        json={"city_slug": city.slug, "type": "geolocation", "lat": 1.0, "lng": 1.0},
    )

    assert points.status_code == 200
    assert points.json()[0]["type"] == "city_center"
    assert resolved.status_code == 200
    assert resolved.json()["out_of_city"] is True
    assert resolved.json()["warnings"][0]["code"] == "GEO_OUT_OF_CITY_FALLBACK"
