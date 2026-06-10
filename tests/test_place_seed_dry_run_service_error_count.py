from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_returns_one_error_per_invalid_item() -> None:
    items = [
        PlaceSeedItem(
            title=" ",
            slug="bad-place-1",
            city_slug="zelenogradsk",
            category="coffee",
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
        PlaceSeedItem(
            title=" ",
            slug="bad-place-2",
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
    assert result.invalid == 2
    assert len(result.errors) == 2
    assert "bad-place-1" in result.errors[0]
    assert "bad-place-2" in result.errors[1]
