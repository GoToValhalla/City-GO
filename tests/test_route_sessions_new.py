import models.route_session  # noqa: F401 - register tables for in-memory metadata
from models.route import Route
from models.route_place import RoutePlace


def test_route_session_full_manual_flow_filters_ineligible_points_new(
    client,
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
):
    monkeypatch.setattr("core.public_access_middleware.assert_web_public", lambda db: None)
    city = city_factory(slug="session-city", name="Сессионный город")
    park = place_factory(
        city_id=city.id,
        slug="session-park",
        title="Парк",
        category="park",
        lat=54.91,
        lng=20.41,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    bank = place_factory(
        city_id=city.id,
        slug="session-bank",
        title="Банк",
        category="bank",
        lat=54.92,
        lng=20.42,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    museum = place_factory(
        city_id=city.id,
        slug="session-museum",
        title="Музей",
        category="museum",
        lat=54.93,
        lng=20.43,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    route = Route(city_id=city.id, slug="session-route", title="Маршрут сессии")
    db_session.add(route)
    db_session.flush()
    db_session.add_all(
        [
            RoutePlace(route_id=route.id, place_id=park.id, position=1),
            RoutePlace(route_id=route.id, place_id=bank.id, position=2),
            RoutePlace(route_id=route.id, place_id=museum.id, position=3),
        ]
    )
    db_session.commit()

    start_response = client.post(f"/routes/{route.id}/sessions", json={"user_key": "web:test-user"})

    assert start_response.status_code == 200
    session = start_response.json()
    assert session["route_id"] == route.id
    assert session["status"] == "active"
    assert session["current_point_index"] == 0
    assert [point["title"] for point in session["points"]] == ["Парк", "Музей"]
    session_id = session["id"]

    first_checkin = client.post(
        f"/route-sessions/{session_id}/events/checkin",
        json={"point_index": 0, "action": "visit"},
    )

    assert first_checkin.status_code == 200
    assert first_checkin.json()["visited_point_indexes"] == [0]
    assert first_checkin.json()["current_point_index"] == 1
    assert first_checkin.json()["status"] == "active"

    second_checkin = client.post(
        f"/route-sessions/{session_id}/events/checkin",
        json={"point_index": 1, "action": "visit"},
    )

    assert second_checkin.status_code == 200
    assert second_checkin.json()["visited_point_indexes"] == [0, 1]
    assert second_checkin.json()["current_point_index"] == 2
    assert second_checkin.json()["status"] == "completed"
    assert second_checkin.json()["completed_at"] is not None

    complete_response = client.post(f"/route-sessions/{session_id}/complete")

    assert complete_response.status_code == 200
    summary = complete_response.json()
    assert summary["status"] == "completed"
    assert summary["visited_points"] == 2
    assert summary["total_points"] == 2


def test_route_session_start_rejects_route_with_less_than_two_valid_points_new(
    client,
    db_session,
    city_factory,
    place_factory,
    monkeypatch,
):
    monkeypatch.setattr("core.public_access_middleware.assert_web_public", lambda db: None)
    city = city_factory(slug="short-session-city", name="Короткий город")
    valid_place = place_factory(
        city_id=city.id,
        slug="short-session-park",
        title="Парк",
        category="park",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
    )
    hidden_place = place_factory(
        city_id=city.id,
        slug="short-session-hidden",
        title="Скрытое место",
        category="museum",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=True,
        publication_status="draft",
    )
    route = Route(city_id=city.id, slug="short-session-route", title="Короткий маршрут")
    db_session.add(route)
    db_session.flush()
    db_session.add_all(
        [
            RoutePlace(route_id=route.id, place_id=valid_place.id, position=1),
            RoutePlace(route_id=route.id, place_id=hidden_place.id, position=2),
        ]
    )
    db_session.commit()

    response = client.post(f"/routes/{route.id}/sessions", json={})

    assert response.status_code == 409
    assert response.json()["detail"] == "route_has_less_than_two_eligible_points"
