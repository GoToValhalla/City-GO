from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_uses_placeholder_for_empty_slug_in_errors() -> None:
    items = [
        PlaceSeedItem(
            title=" ",
            slug=" ",
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
        )
    ]

    result = run_place_seed_dry_run(items)

    assert result.total == 1
    assert result.invalid == 1
    assert len(result.errors) == 1
    assert "<empty-slug>" in result.errors[0]
