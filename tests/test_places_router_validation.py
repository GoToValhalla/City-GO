from fastapi.testclient import TestClient

from main import app


def test_read_places_rejects_limit_less_than_one() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_read_places_rejects_negative_offset() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/",
        params={
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_search_places_rejects_limit_more_than_one_hundred() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "limit": 101,
        },
    )

    assert response.status_code == 422
