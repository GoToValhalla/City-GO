import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.request_logging import log_request
from db.dependencies import get_db
from routers.nearby import router


@pytest.fixture
def nearby_client(db_session):
    app = FastAPI()
    app.include_router(router)
    app.middleware("http")(log_request)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def test_nearby_rejects_invalid_coordinates_and_radius_new(nearby_client):
    assert nearby_client.get("/nearby/?lat=91&lng=20&radius_km=1").status_code == 422
    assert nearby_client.get("/nearby/?lat=54&lng=181&radius_km=1").status_code == 422
    assert nearby_client.get("/nearby/?lat=0&lng=0&radius_km=1").status_code == 422
    assert nearby_client.get("/nearby/?lat=54&lng=20&radius_km=0.01").status_code == 422
    assert nearby_client.get("/nearby/?lat=54&lng=20&radius_km=51").status_code == 422


def test_nearby_sorts_by_distance_and_suggests_city_new(
    nearby_client, city_factory, place_factory,
):
    city = city_factory(
        slug="geo-city", name="Гео", is_active=True,
        center_lat=54.9, center_lng=20.4,
    )
    near = place_factory(city_id=city.id, lat=54.9001, lng=20.4001)
    far = place_factory(city_id=city.id, lat=54.91, lng=20.41)
    response = nearby_client.get("/nearby/?lat=54.9&lng=20.4&radius_km=5")
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert ids.index(near.id) < ids.index(far.id)
    suggestion = nearby_client.get("/nearby/nearest-city?lat=54.9&lng=20.4").json()
    assert suggestion["city_slug"] == city.slug


def test_request_logs_do_not_contain_coordinates_new(nearby_client, caplog):
    caplog.set_level(logging.INFO, logger="citygo.api.requests")
    nearby_client.get("/nearby/?lat=54.987654&lng=20.123456&radius_km=1")
    payloads = [json.loads(row.message) for row in caplog.records if row.message.startswith("{")]
    assert payloads
    assert all("54.987654" not in json.dumps(payload) for payload in payloads)
