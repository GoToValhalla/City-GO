from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_passes_all_filters() -> None:
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
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import place_search

    original_get_places = place_search.get_places
    original_get_places_total = place_search.get_places_total

    place_search.get_places = fake_get_places
    place_search.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "city_id": 1,
            "city_slug": "zelenogradsk",
            "category_id": 2,
            "tag_id": 3,
            "limit": 5,
            "offset": 10,
        },
    )

    place_search.get_places = original_get_places
    place_search.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["city_id"] == 1
    assert captured["city_slug"] == "zelenogradsk"
    assert captured["category_id"] == 2
    assert captured["tag_id"] == 3
    assert captured["q"] == "coffee"
    assert captured["limit"] == 5
    assert captured["offset"] == 10
    assert captured["sort_by"] == "title"
    assert captured["sort_order"] == "asc"