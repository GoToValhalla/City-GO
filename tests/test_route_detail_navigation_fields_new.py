from models.route import Route
from models.route_place import RoutePlace


def test_route_detail_returns_navigation_point_fields_new(
    client,
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
):
    monkeypatch.setattr("core.public_access_middleware.assert_web_public", lambda db: None)
    city = city_factory(slug="navigation-city", name="Навигация")
    place = place_factory(
        city_id=city.id,
        slug="navigation-park",
        title="Парк навигации",
        category="park",
        address="Парковая 1",
        lat=54.91,
        lng=20.41,
        is_published=True,
        is_route_eligible=True,
        publication_status="published",
        is_active=True,
    )
    place2 = place_factory(
        city_id=city.id,
        slug="navigation-cafe",
        title="Кафе навигации",
        category="cafe",
        address="Парковая 2",
        lat=54.911,
        lng=20.411,
        is_published=True,
        is_route_eligible=True,
        publication_status="published",
        is_active=True,
    )
    route = Route(city_id=city.id, slug="navigation-route", title="Маршрут навигации")
    db_session.add(route)
    db_session.flush()
    db_session.add(RoutePlace(route_id=route.id, place_id=place.id, position=1))
    db_session.add(RoutePlace(route_id=route.id, place_id=place2.id, position=2))
    db_session.commit()

    response = client.get("/routes/by-slug/navigation-route")

    assert response.status_code == 200
    point = response.json()["points"][0]
    assert point["lat"] == 54.91
    assert point["lng"] == 20.41
    assert point["category"] == "park"
    assert point["address"] == "Парковая 1"
    assert point["is_published"] is True
    assert point["is_route_eligible"] is True
    assert point["publication_status"] == "published"
    assert point["is_active"] is True
    assert len(response.json()["points"]) == 2
