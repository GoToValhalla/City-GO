from fastapi.testclient import TestClient

from main import app


def test_search_places_requires_q() -> None:
    client = TestClient(app)

    response = client.get("/places/search/")

    assert response.status_code == 422
