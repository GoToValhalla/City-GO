from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from models.route import Route
from models.route_place import RoutePlace

_AUTH = {"Authorization": "Bearer test"}


def _route(db_session, city_id: int, title: str = "Маршрут", distance_km: float | None = None) -> Route:
    route = Route(city_id=city_id, slug=f"route-{title}", title=title, route_mode="walk", is_active=True, distance_km=distance_km)
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    return route


def _link(db_session, route: Route, place, position: int) -> None:
    db_session.add(RoutePlace(route_id=route.id, place_id=place.id, position=position))
    db_session.commit()


def test_route_health_detects_min_points_and_service_places_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="health-city")
    museum = published_place_factory(city_id=city.id, category="museum", title="Музей")
    pharmacy = published_place_factory(city_id=city.id, category="pharmacy", title="Аптека")
    route = _route(db_session, city.id, "health-short")
    _link(db_session, route, museum, 1)
    _link(db_session, route, pharmacy, 2)

    response = client.get("/admin/route-health?city_slug=health-city", headers=_AUTH)
    assert response.status_code == 200
    body = response.json()
    codes = {issue["code"] for issue in body["issues"]}
    assert "route_min_points_failed" in codes
    assert "route_service_places_detected" in codes
    assert body["status"] == "critical"


def test_route_health_detects_city_mixing_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="route-city-a")
    other = city_factory(slug="route-city-b", name="Другой город")
    place_a = published_place_factory(city_id=city.id, category="museum", title="Музей A")
    place_b = published_place_factory(city_id=other.id, category="museum", title="Музей B")
    place_c = published_place_factory(city_id=city.id, category="park", title="Парк C")
    route = _route(db_session, city.id, "mixed-city")
    _link(db_session, route, place_a, 1)
    _link(db_session, route, place_b, 2)
    _link(db_session, route, place_c, 3)

    response = client.get("/admin/route-health?city_slug=route-city-a", headers=_AUTH)
    assert response.status_code == 200
    codes = {issue["code"] for issue in response.json()["issues"]}
    assert "route_city_mixing_error" in codes


def test_route_health_rerun_returns_backend_read_model_new(client: TestClient, city_factory) -> None:
    city_factory(slug="rerun-city")
    response = client.post("/admin/route-health/re-run?city_slug=rerun-city", headers=_AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert set(body["result"]) >= {"routes_checked", "issues", "status", "checked_at"}


def test_route_health_detects_long_transition_warning_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="route-long-city")
    first = published_place_factory(city_id=city.id, category="museum", title="Музей")
    second = published_place_factory(city_id=city.id, category="park", title="Парк")
    route = _route(db_session, city.id, "long-transition", distance_km=7.2)
    _link(db_session, route, first, 1)
    _link(db_session, route, second, 2)

    response = client.get("/admin/route-health?city_slug=route-long-city", headers=_AUTH)
    assert response.status_code == 200
    codes = {issue["code"] for issue in response.json()["issues"]}
    assert "route_long_transition_warning" in codes


def test_route_health_detects_low_diversity_warning_new(client: TestClient, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="route-diversity-city")
    route = _route(db_session, city.id, "low-diversity")
    for index in range(4):
        place = published_place_factory(city_id=city.id, category="cafe", title=f"Кафе {index}")
        _link(db_session, route, place, index + 1)

    response = client.get("/admin/route-health?city_slug=route-diversity-city", headers=_AUTH)
    assert response.status_code == 200
    codes = {issue["code"] for issue in response.json()["issues"]}
    assert "route_low_diversity_warning" in codes
