from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_bulk_result() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={
            "items": [
                {
                    "title": "Coffee Point",
                    "slug": "coffee-point",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": "Kurortny Prospekt 12",
                    "short_description": "Good coffee place",
                    "taxonomy": {
                        "category": "coffee",
                        "tags": ["pet_friendly", "quiet"],
                        "scenario_tags": ["coffee_now", "with_dog"],
                        "vibe_tags": ["cozy"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.964,
                    "lng": 20.475,
                    "is_active": True,
                },
                {
                    "title": " ",
                    "slug": "bad-place",
                    "city_slug": "zelenogradsk",
                    "category": "food",
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

    data = response.json()
    assert data["total"] == 2
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 1
    assert len(data["items"]) == 2
    assert data["items"][0]["is_valid"] is True
    assert data["items"][1]["is_valid"] is False