from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_taxonomy_errors() -> None:
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
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": ["bad_scenario"],
                        "vibe_tags": ["bad_vibe"],
                        "restriction_tags": ["bad_restriction"],
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

    item = data["items"][0]
    assert item["is_valid"] is False
    assert item["taxonomy_diagnostics"] == {
        "category": "bad_category",
        "tags": ["bad_tag"],
        "scenario_tags": ["bad_scenario"],
        "vibe_tags": ["bad_vibe"],
        "restriction_tags": ["bad_restriction"],
    }
