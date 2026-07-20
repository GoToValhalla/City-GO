from fastapi.testclient import TestClient

from core.config import settings
from main import app

_TOKEN = "test-place-seed-admin-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def test_dry_run_place_seed_payload_returns_invalid_for_all_invalid_items(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _TOKEN)
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        headers=_HEADERS,
        json={
            "items": [
                {
                    "title": " ",
                    "slug": "bad-place-1",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
                {
                    "title": " ",
                    "slug": "bad-place-2",
                    "city_slug": "zelenogradsk",
                    "category": "walk",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["created"] == 0
    assert response.json()["updated"] == 0
    assert response.json()["skipped"] == 0
    assert response.json()["invalid"] == 2
    assert len(response.json()["errors"]) == 2
