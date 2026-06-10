from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_bulk_validation_service import validate_place_seed_items


def test_validate_place_seed_items_returns_bulk_stats() -> None:
    items = [
        PlaceSeedItem(
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
        ),
        PlaceSeedItem(
            title=" ",
            slug="bad-place",
            city_slug="zelenogradsk",
            category="food",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        ),
    ]

    result = validate_place_seed_items(items)

    assert result.total == 2
    assert result.valid_count == 1
    assert result.invalid_count == 1
    assert len(result.items) == 2
    assert result.items[0].is_valid is True
    assert result.items[1].is_valid is False
