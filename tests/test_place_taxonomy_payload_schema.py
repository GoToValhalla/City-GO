from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


def test_place_taxonomy_payload_defaults() -> None:
    payload = PlaceTaxonomyPayload(category="coffee")

    assert payload.category == "coffee"
    assert payload.tags == []
    assert payload.scenario_tags == []
    assert payload.vibe_tags == []
    assert payload.restriction_tags == []


def test_place_taxonomy_payload_accepts_full_payload() -> None:
    payload = PlaceTaxonomyPayload(
        category="food",
        tags=["local_food", "quiet"],
        scenario_tags=["food_now", "evening_plan"],
        vibe_tags=["authentic", "cozy"],
        restriction_tags=["reservation_needed"],
    )

    assert payload.category == "food"
    assert payload.tags == ["local_food", "quiet"]
    assert payload.scenario_tags == ["food_now", "evening_plan"]
    assert payload.vibe_tags == ["authentic", "cozy"]
    assert payload.restriction_tags == ["reservation_needed"]
