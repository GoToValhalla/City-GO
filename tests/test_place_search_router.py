from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app
from schemas.public_place import (
    PublicCategory,
    PublicCoordinates,
    PublicDataQuality,
    PublicPlaceRead,
)


def test_search_places_returns_structured_response(monkeypatch) -> None:
    public_item = PublicPlaceRead(
        id=1,
        slug="coffee-point",
        name="Coffee Point",
        title="Coffee Point",
        category="coffee",
        category_label="Coffee",
        category_info=PublicCategory(slug="coffee", label="Coffee"),
        coordinates=PublicCoordinates(lat=54.964, lng=20.475),
        lat=54.964,
        lng=20.475,
        data_quality=PublicDataQuality(is_degraded=False, completeness_score=80),
    )

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
        return [object()]

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

    def fake_build_public_place_reads(db, places):
        assert len(places) == 1
        return [public_item]

    def fake_get_db():
        yield object()

    monkeypatch.setattr("routers.place_search.get_places", fake_get_places)
    monkeypatch.setattr("routers.place_search.get_places_total", fake_get_places_total)
    monkeypatch.setattr(
        "routers.place_search.build_public_place_reads", fake_build_public_place_reads
    )
    monkeypatch.setattr("routers.place_search.is_toggle_enabled", lambda *args, **kwargs: False)
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
    assert "publication_status" not in data["items"][0]

    app.dependency_overrides.clear()
