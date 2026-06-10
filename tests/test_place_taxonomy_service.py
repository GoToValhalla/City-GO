from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
    validate_tag_list,
)


def test_is_valid_place_category() -> None:
    assert is_valid_place_category("coffee") is True
    assert is_valid_place_category("coworking") is False


def test_is_valid_place_tag() -> None:
    assert is_valid_place_tag("pet_friendly") is True
    assert is_valid_place_tag("dog_friendly") is False


def test_is_valid_place_scenario_tag() -> None:
    assert is_valid_place_scenario_tag("with_dog") is True
    assert is_valid_place_scenario_tag("dog_walk_now") is False


def test_is_valid_place_vibe_tag() -> None:
    assert is_valid_place_vibe_tag("cozy") is True
    assert is_valid_place_vibe_tag("luxury") is False


def test_is_valid_place_restriction_tag() -> None:
    assert is_valid_place_restriction_tag("cash_only") is True
    assert is_valid_place_restriction_tag("pets_inside_only") is False


def test_validate_tag_list_filters_invalid_and_removes_duplicates() -> None:
    values = [
        "pet_friendly",
        "quiet",
        "pet_friendly",
        "invalid_tag",
        "budget",
    ]

    result = validate_tag_list(values, is_valid_place_tag)

    assert result == [
        "pet_friendly",
        "quiet",
        "budget",
    ]
