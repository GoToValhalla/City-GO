from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_validation_service import validate_place_seed_item


def test_validate_place_seed_item_returns_valid_for_clean_seed() -> None:
    item = PlaceSeedItem(
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        category="coffee",
        address="Kurortny Prospekt 12",
        short_description="Good coffee place",
        taxonomy=PlaceTaxonomyPayload(
            category="coffee",
            tags=["pet_friendly", "quiet"],
            scenario_tags=["coffee_now", "with_dog"],
            vibe_tags=["cozy"],
            restriction_tags=[],
        ),
        source="manual",
        source_url=None,
        lat=54.964,
        lng=20.475,
        is_active=True,
    )

    result = validate_place_seed_item(item)

    assert result.is_valid is True
    assert result.errors == []
    assert result.taxonomy_diagnostics.category is None
    assert result.taxonomy_diagnostics.tags == []
    assert result.taxonomy_diagnostics.scenario_tags == []
    assert result.taxonomy_diagnostics.vibe_tags == []
    assert result.taxonomy_diagnostics.restriction_tags == []


def test_validate_place_seed_item_returns_errors_for_empty_fields_and_bad_taxonomy() -> None:
    item = PlaceSeedItem(
        title=" ",
        slug=" ",
        city_slug=" ",
        category="coffee",
        address=None,
        short_description=None,
        taxonomy=PlaceTaxonomyPayload(
            category="bad_category",
            tags=["bad_tag"],
            scenario_tags=["bad_scenario"],
            vibe_tags=["bad_vibe"],
            restriction_tags=["bad_restriction"],
        ),
        source=None,
        source_url=None,
        lat=None,
        lng=None,
        is_active=True,
    )

    result = validate_place_seed_item(item)

    assert result.is_valid is False
    assert "title is empty" in result.errors
    assert "slug is empty" in result.errors
    assert "city_slug is empty" in result.errors
    assert result.taxonomy_diagnostics.category == "bad_category"
    assert result.taxonomy_diagnostics.tags == ["bad_tag"]
    assert result.taxonomy_diagnostics.scenario_tags == ["bad_scenario"]
    assert result.taxonomy_diagnostics.vibe_tags == ["bad_vibe"]
    assert result.taxonomy_diagnostics.restriction_tags == ["bad_restriction"]