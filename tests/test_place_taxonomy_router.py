from fastapi.testclient import TestClient

from main import app


def test_read_place_taxonomy_returns_canonical_structure() -> None:
    client = TestClient(app)

    response = client.get("/place-taxonomy/")

    assert response.status_code == 200

    data = response.json()

    assert "categories" in data
    assert "tags" in data
    assert "scenario_tags" in data
    assert "vibe_tags" in data
    assert "restriction_tags" in data
    assert "user_signals" in data

    assert "coffee" in data["categories"]
    assert "pet_friendly" in data["tags"]
    assert "with_dog" in data["scenario_tags"]
    assert "cozy" in data["vibe_tags"]
    assert "cash_only" in data["restriction_tags"]
    assert "view_place" in data["user_signals"]
