from services.place_taxonomy_response_service import build_place_taxonomy_response


def test_build_place_taxonomy_response_returns_expected_structure() -> None:
    response = build_place_taxonomy_response()

    assert "coffee" in response.categories
    assert "pet_friendly" in response.tags
    assert "with_dog" in response.scenario_tags
    assert "cozy" in response.vibe_tags
    assert "cash_only" in response.restriction_tags
    assert "view_place" in response.user_signals
