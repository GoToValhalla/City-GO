from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)


def test_get_invalid_place_taxonomy_values_returns_empty_invalid_lists_for_valid_payload() -> None:
    payload = PlaceTaxonomyPayload(
        category="coffee",
        tags=["pet_friendly", "quiet"],
        scenario_tags=["coffee_now", "with_dog"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
    )

    result = get_invalid_place_taxonomy_values(payload)

    assert result.category is None
    assert result.tags == []
    assert result.scenario_tags == []
    assert result.vibe_tags == []
    assert result.restriction_tags == []


def test_get_invalid_place_taxonomy_values_returns_only_invalid_values() -> None:
    payload = PlaceTaxonomyPayload(
        category="invalid_category",
        tags=["pet_friendly", "bad_tag"],
        scenario_tags=["with_dog", "bad_scenario"],
        vibe_tags=["cozy", "bad_vibe"],
        restriction_tags=["cash_only", "bad_restriction"],
    )

    result = get_invalid_place_taxonomy_values(payload)

    assert result.category == "invalid_category"
    assert result.tags == ["bad_tag"]
    assert result.scenario_tags == ["bad_scenario"]
    assert result.vibe_tags == ["bad_vibe"]
    assert result.restriction_tags == ["bad_restriction"]
