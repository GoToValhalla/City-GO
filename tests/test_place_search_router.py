from datetime import datetime

from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_returns_structured_response(monkeypatch) -> None:
    expected_items = [
        {
            "id": 1,
            "title": "Coffee Point",
            "slug": "coffee-point",
            "city_id": 1,
            "category_id": 2,
            "short_description": "Good coffee place",
            "category": "coffee",
            "address": "Kurortny Prospekt 12",
            "lat": 54.964,
            "lng": 20.475,
            "price_level": 1,
            "dog_friendly": False,
            "family_friendly": False,
            "indoor": False,
            "outdoor": False,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by="title",
        sort_order="asc",
    ):
        assert city_slug == "zelenogradsk"
        assert q == "coffee"
        assert limit == 20
        assert offset == 0
        return expected_items

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        assert city_slug == "zelenogradsk"
        assert q == "coffee"
        return 1

    def fake_get_db():
        yield object()

    monkeypatch.setattr("routers.place_search.get_places", fake_get_places)
    monkeypatch.setattr("routers.place_search.get_places_total", fake_get_places_total)
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "city_slug": "zelenogradsk",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "coffee-point"
    assert data["items"][0]["title"] == "Coffee Point"

    app.dependency_overrides.clear()