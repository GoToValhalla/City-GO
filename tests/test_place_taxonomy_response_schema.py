from schemas.place_taxonomy_response import PlaceTaxonomyResponse


def test_place_taxonomy_response_defaults() -> None:
    response = PlaceTaxonomyResponse()

    assert response.categories == []
    assert response.tags == []
    assert response.scenario_tags == []
    assert response.vibe_tags == []
    assert response.restriction_tags == []
    assert response.user_signals == []


def test_place_taxonomy_response_accepts_full_payload() -> None:
    response = PlaceTaxonomyResponse(
        categories=["coffee", "food"],
        tags=["pet_friendly", "quiet"],
        scenario_tags=["with_dog", "coffee_now"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
        user_signals=["view_place", "save_place"],
    )

    assert response.categories == ["coffee", "food"]
    assert response.tags == ["pet_friendly", "quiet"]
    assert response.scenario_tags == ["with_dog", "coffee_now"]
    assert response.vibe_tags == ["cozy", "local_favorite"]
    assert response.restriction_tags == ["cash_only"]
    assert response.user_signals == ["view_place", "save_place"]
