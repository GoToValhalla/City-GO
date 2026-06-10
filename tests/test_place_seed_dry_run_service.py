from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_counts_valid_as_skipped_and_invalid_as_invalid() -> None:
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

    result = run_place_seed_dry_run(items)

    assert result.total == 2
    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 1
    assert result.invalid == 1
    assert len(result.errors) == 1
    assert "bad-place" in result.errors[0]


def test_run_place_seed_dry_run_returns_empty_summary_for_empty_list() -> None:
    result = run_place_seed_dry_run([])

    assert result.total == 0
    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 0
    assert result.invalid == 0
    assert result.errors == []
