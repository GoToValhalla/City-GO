from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


def test_place_seed_item_accepts_minimal_valid_payload() -> None:
    item = PlaceSeedItem(
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee"),
    )

    assert item.title == "Coffee Point"
    assert item.slug == "coffee-point"
    assert item.city_slug == "zelenogradsk"
    assert item.category == "coffee"
    assert item.is_active is True
    assert item.address is None
    assert item.short_description is None
    assert item.source is None
    assert item.source_url is None
    assert item.lat is None
    assert item.lng is None


def test_place_seed_item_accepts_full_payload() -> None:
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
            restriction_tags=["cash_only"],
        ),
        source="manual",
        source_url="https://example.com",
        last_verified_at="2026-06-04",
        lat=54.964,
        lng=20.475,
        opening_hours={"mon": {"open": "09:00", "close": "18:00"}},
        average_visit_duration_minutes=45,
        price_level=2,
        is_active=False,
    )

    assert item.address == "Kurortny Prospekt 12"
    assert item.short_description == "Good coffee place"
    assert item.taxonomy.category == "coffee"
    assert item.source == "manual"
    assert item.source_url == "https://example.com"
    assert item.lat == 54.964
    assert item.lng == 20.475
    assert item.opening_hours == {"mon": {"open": "09:00", "close": "18:00"}}
    assert item.average_visit_duration_minutes == 45
    assert item.price_level == 2
    assert item.last_verified_at is not None
    assert item.is_active is False
