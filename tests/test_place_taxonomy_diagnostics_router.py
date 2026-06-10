from fastapi.testclient import TestClient

from main import app


def test_validate_place_taxonomy_payload_returns_invalid_values() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-taxonomy/diagnostics/",
        json={
            "category": "invalid_category",
            "tags": ["pet_friendly", "bad_tag"],
            "scenario_tags": ["with_dog", "bad_scenario"],
            "vibe_tags": ["cozy", "bad_vibe"],
            "restriction_tags": ["cash_only", "bad_restriction"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": "invalid_category",
        "tags": ["bad_tag"],
        "scenario_tags": ["bad_scenario"],
        "vibe_tags": ["bad_vibe"],
        "restriction_tags": ["bad_restriction"],
    }


def test_validate_place_taxonomy_payload_returns_empty_invalid_values_for_valid_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-taxonomy/diagnostics/",
        json={
            "category": "coffee",
            "tags": ["pet_friendly", "quiet"],
            "scenario_tags": ["coffee_now", "with_dog"],
            "vibe_tags": ["cozy", "local_favorite"],
            "restriction_tags": ["cash_only"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": None,
        "tags": [],
        "scenario_tags": [],
        "vibe_tags": [],
        "restriction_tags": [],
    }
