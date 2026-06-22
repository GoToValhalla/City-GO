from fastapi.testclient import TestClient

from main import app


def test_cities_available_hides_draft(client: TestClient, db_session):
    from models.city import City
    db_session.add(City(slug="zelenogradsk", name="Зеленоградск", country="Россия", launch_status="published", is_active=True))
    db_session.add(City(slug="kutaisi", name="Кутаиси", country="Грузия", launch_status="draft"))
    db_session.commit()
    response = client.get("/cities/available")
    assert [item["slug"] for item in response.json()] == ["zelenogradsk"]


def test_city_by_slug_route_is_not_shadowed_by_city_id(client: TestClient, db_session):
    from models.city import City
    db_session.add(City(slug="zelenogradsk", name="Зеленоградск", country="Россия", launch_status="published", is_active=True))
    db_session.commit()
    response = client.get("/cities/by-slug/zelenogradsk")
    assert response.status_code == 200
    assert response.json()["slug"] == "zelenogradsk"


def test_place_discovery_endpoint_creates_review_request(client: TestClient, db_session):
    from models.city import City
    db_session.add(City(slug="zelenogradsk", name="Зеленоградск", country="Россия"))
    db_session.commit()
    response = client.post("/place-discovery/", json={"city_slug": "zelenogradsk", "name": "Кафе X"})
    assert response.status_code == 200
    assert response.json()["status"] == "new"
