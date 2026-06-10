from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_skipped_for_all_valid_items() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
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
                    "title": "Walk Route",
                    "slug": "walk-route",
                    "city_slug": "zelenogradsk",
                    "category": "walk",
                    "address": "Promenade",
                    "short_description": "Nice walk by the sea",
                    "taxonomy": {
                        "category": "walk",
                        "tags": ["outdoor", "photo_spot"],
                        "scenario_tags": ["walk_now", "weekend_plan"],
                        "vibe_tags": ["calm"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.965,
                    "lng": 20.476,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "created": 0,
        "updated": 0,
        "skipped": 2,
        "invalid": 0,
        "errors": [],
        "auto_published": 0,
        "needs_review_count": 0,
        "rejected_count": 0,
    }
