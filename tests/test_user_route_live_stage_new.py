from __future__ import annotations

from fastapi.testclient import TestClient


def _payload(city_slug: str) -> dict[str, object]:
    return {
        "lat": 54.9611,
        "lng": 20.4703,
        "start_source": "city_center",
        "build_mode": "auto",
        "time_budget_minutes": 180,
        "route_time_mode": "flexible",
        "interests": [],
        "avoided_categories": [],
        "excluded_place_ids": [],
        "city_id": city_slug,
        "user_id": "route-stage-test",
    }


def _route_place(db_session, published_place_factory, *, city_id: int, category: str, index: int):
    place = published_place_factory(
        city_id=city_id,
        category=category,
        title=f"Туристическое место {index}",
        slug=f"route-stage-{category}-{index}",
        lat=54.9611 + index * 0.001,
        lng=20.4703 + index * 0.001,
        address=f"Улица {index}",
        image_url=f"https://example.com/place-{index}.jpg",
    )
    place.canonical_category = category
    place.quality_tier = "gold"
    place.quality_score = 80
    place.completeness_score = 30
    place.photo_score = 20
    place.description_score = 10
    place.confidence_score = 8
    db_session.commit()
    db_session.refresh(place)
    return place


def test_live_route_preview_returns_at_least_three_tourist_points_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="live-route-city")
    places = [
        _route_place(db_session, published_place_factory, city_id=city.id, category=category, index=index)
        for index, category in enumerate(("museum", "park", "landmark", "viewpoint"), start=1)
    ]

    response = client.post("/v1/user-routes/preview", json=_payload(city.slug))

    assert response.status_code == 200
    body = response.json()
    point_ids = {int(point["place_id"]) for point in body["points"]}
    assert body["status"] in {"preview", "partial_route"}
    assert body["total_places"] >= 3
    assert len(point_ids & {place.id for place in places}) >= 3


def test_live_route_preview_excludes_service_places_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="live-route-service-city")
    for index, category in enumerate(("museum", "park", "landmark", "viewpoint"), start=1):
        _route_place(db_session, published_place_factory, city_id=city.id, category=category, index=index)
    pharmacy = _route_place(db_session, published_place_factory, city_id=city.id, category="pharmacy", index=9)

    response = client.post("/v1/user-routes/preview", json=_payload(city.slug))

    assert response.status_code == 200
    body = response.json()
    point_ids = {int(point["place_id"]) for point in body["points"]}
    assert pharmacy.id not in point_ids
    assert body["total_places"] >= 3


def test_live_route_preview_excludes_internal_service_only_places_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="live-route-internal-service-city")
    for index, category in enumerate(("museum", "park", "landmark", "viewpoint"), start=1):
        _route_place(db_session, published_place_factory, city_id=city.id, category=category, index=index)
    service = _route_place(db_session, published_place_factory, city_id=city.id, category="museum", index=12)
    service.internal_status = "service_only"
    db_session.commit()

    response = client.post("/v1/user-routes/preview", json=_payload(city.slug))

    assert response.status_code == 200
    assert service.id not in {int(point["place_id"]) for point in response.json()["points"]}
