from types import SimpleNamespace

from services.public_place_quality import (
    NON_TOURIST_CATEGORIES,
    is_non_tourist_category,
    is_public_place_visible,
    is_public_route_place_eligible,
    is_technical_osm_title,
)


def _place(**overrides):
    data = {
        "is_active": True,
        "status": "active",
        "is_published": True,
        "is_visible_in_catalog": True,
        "publication_status": "published",
        "is_spam_poi": False,
        "canonical_category": None,
        "category": "museum",
        "title": "Городской музей",
        "is_route_eligible": True,
        "lat": 61.0,
        "lng": 69.0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_public_quality_gate_blocks_non_tourist_categories_new() -> None:
    for category in ("bank", "atm", "police", "mvd", "service", "transport", "pharmacy", "hospital"):
        assert category in NON_TOURIST_CATEGORIES
        assert is_non_tourist_category(category)
        assert not is_public_place_visible(_place(category=category))


def test_public_quality_gate_uses_canonical_category_new() -> None:
    assert not is_public_place_visible(_place(category="coffee", canonical_category="bank"))


def test_public_quality_gate_blocks_technical_titles_new() -> None:
    for title in ("node/123", "way 456", "relation-789", "OSM:123", "место OSM 42", "12345"):
        assert is_technical_osm_title(title)
        assert not is_public_place_visible(_place(title=title))


def test_public_route_gate_requires_route_fields_new() -> None:
    assert is_public_route_place_eligible(_place())
    assert not is_public_route_place_eligible(_place(is_route_eligible=False))
    assert not is_public_route_place_eligible(_place(lat=None))
    assert not is_public_route_place_eligible(_place(lng=None))
