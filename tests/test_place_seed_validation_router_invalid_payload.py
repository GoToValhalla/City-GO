from fastapi.testclient import TestClient

from core.config import settings
from main import app

_TOKEN = "test-place-seed-admin-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def test_validate_place_seed_payload_returns_invalid_result_for_empty_required_fields(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _TOKEN)
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        headers=_HEADERS,
        json={
            "items": [
                {
                    "title": " ",
                    "slug": " ",
                    "city_slug": " ",
                    "category": "coffee",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "coffee",
                        "tags": [],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["valid_count"] == 0
    assert data["invalid_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["is_valid"] is False
    assert "title is empty" in data["items"][0]["errors"]
    assert "slug is empty" in data["items"][0]["errors"]
    assert "city_slug is empty" in data["items"][0]["errors"]
