from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dedup_service import deduplicate_place_seed_items
from services.place_seed_normalization_service import normalize_place_seed_item
from services.place_seed_payload_service import place_payload


def _item(slug: str = " Coffee Place ") -> PlaceSeedItem:
    return PlaceSeedItem(
        title="  Coffee   Place ",
        slug=slug,
        city_slug=" Zelenogradsk ",
        category=" Coffee ",
        taxonomy=PlaceTaxonomyPayload(
            category="coffee",
            tags=["indoor", "pet_friendly"],
            scenario_tags=["with_dog"],
            vibe_tags=[],
            restriction_tags=[],
        ),
        lat=54.96,
        lng=20.48,
        opening_hours={"mon": {"open": "09:00", "close": "18:00"}},
        average_visit_duration_minutes=30,
        price_level=2,
        last_verified_at="2026-06-04",
        source="OSM",
        source_url="https://example.test/place",
        confidence=0.8,
    )


def test_normalize_place_seed_item_cleans_identity_fields() -> None:
    item = normalize_place_seed_item(_item())
    assert item.title == "Coffee Place"
    assert item.slug == "coffee-place"
    assert item.city_slug == "zelenogradsk"
    assert item.category == "coffee"


def test_deduplicate_place_seed_items_keeps_first_slug() -> None:
    first = normalize_place_seed_item(_item("coffee-place"))
    second = normalize_place_seed_item(_item("coffee-place"))
    result = deduplicate_place_seed_items([first, second])
    assert result.unique_items == [first]
    assert result.duplicate_slugs == ["coffee-place"]


def test_place_payload_maps_taxonomy_flags() -> None:
    payload = place_payload(normalize_place_seed_item(_item()), city_id=1, category_id=2)
    assert payload["city_id"] == 1
    assert payload["category_id"] == 2
    assert payload["indoor"] is True
    assert payload["dog_friendly"] is True
    assert payload["source"] == "osm"
    assert payload["confidence"] == 0.8
    assert payload["status"] == "active"
    assert payload["opening_hours"] == {"mon": {"open": "09:00", "close": "18:00"}}
    assert payload["average_visit_duration_minutes"] == 30
    assert payload["price_level"] == 2
    assert payload["last_verified_at"] is not None
