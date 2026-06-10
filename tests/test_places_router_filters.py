from datetime import datetime

from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_read_places_passes_all_filters_and_returns_structured_response() -> None:
    captured: dict[str, object] = {}

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
        captured["city_id"] = city_id
        captured["city_slug"] = city_slug
        captured["category_id"] = category_id
        captured["tag_id"] = tag_id
        captured["q"] = q
        captured["limit"] = limit
        captured["offset"] = offset
        captured["sort_by"] = sort_by
        captured["sort_order"] = sort_order
        return [
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

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 1

    def fake_get_db():
        yield object()

    from routers import places

    original_get_places = places.get_places
    original_get_places_total = places.get_places_total
    places.get_places = fake_get_places
    places.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/",
        params={
            "city_id": 1,
            "city_slug": "zelenogradsk",
            "category_id": 2,
            "tag_id": 3,
            "q": "coffee",
            "limit": 5,
            "offset": 10,
        },
    )

    places.get_places = original_get_places
    places.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 5
    assert data["offset"] == 10
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "coffee-point"
    assert data["items"][0]["title"] == "Coffee Point"

    assert captured["city_id"] == 1
    assert captured["city_slug"] == "zelenogradsk"
    assert captured["category_id"] == 2
    assert captured["tag_id"] == 3
    assert captured["q"] == "coffee"
    assert captured["limit"] == 5
    assert captured["offset"] == 10
    assert captured["sort_by"] == "title"
    assert captured["sort_order"] == "asc"