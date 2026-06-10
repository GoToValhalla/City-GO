from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_read_places_passes_limit_and_offset_and_returns_structured_response() -> None:
    captured: dict[str, int] = {}

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by='title',
        sort_order='asc',
    ):
        captured["limit"] = limit
        captured["offset"] = offset
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
            "limit": 7,
            "offset": 14,
        },
    )

    places.get_places = original_get_places
    places.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["limit"] == 7
    assert captured["offset"] == 14
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 7,
        "offset": 14,
    }