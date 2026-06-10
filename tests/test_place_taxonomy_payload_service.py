from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_payload_service import normalize_place_taxonomy_payload


def test_normalize_place_taxonomy_payload_keeps_valid_values() -> None:
    payload = PlaceTaxonomyPayload(
        category="coffee",
        tags=["pet_friendly", "quiet"],
        scenario_tags=["coffee_now", "with_dog"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
    )

    normalized = normalize_place_taxonomy_payload(payload)

    assert normalized.category == "coffee"
    assert normalized.tags == ["pet_friendly", "quiet"]
    assert normalized.scenario_tags == ["coffee_now", "with_dog"]
    assert normalized.vibe_tags == ["cozy", "local_favorite"]
    assert normalized.restriction_tags == ["cash_only"]


def test_normalize_place_taxonomy_payload_filters_invalid_and_duplicates() -> None:
    payload = PlaceTaxonomyPayload(
        category="invalid_category",
        tags=["pet_friendly", "pet_friendly", "bad_tag"],
        scenario_tags=["with_dog", "bad_scenario"],
        vibe_tags=["cozy", "bad_vibe"],
        restriction_tags=["cash_only", "bad_restriction"],
    )

    normalized = normalize_place_taxonomy_payload(payload)

    assert normalized.category == ""
    assert normalized.tags == ["pet_friendly"]
    assert normalized.scenario_tags == ["with_dog"]
    assert normalized.vibe_tags == ["cozy"]
    assert normalized.restriction_tags == ["cash_only"]
