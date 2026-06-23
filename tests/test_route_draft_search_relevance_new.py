from types import SimpleNamespace

from services.route_draft_search import _matches_search
from services.route_draft_rules import ROUTE_DRAFT_BLOCKED_CATEGORIES


def _place(title: str, category: str, address: str | None = None):
    return SimpleNamespace(title=title, category=category, address=address)


def test_coffee_query_does_not_match_service_or_bank_by_quality_only_new() -> None:
    assert not _matches_search(_place("VTB", "service"), "кофе", "cafe")
    assert not _matches_search(_place("Газпромбанк", "service"), "кофе", "cafe")


def test_coffee_query_keeps_named_coffee_places_even_with_food_category_new() -> None:
    assert _matches_search(_place("Coffee Like", "food"), "кофе", "cafe")
    assert _matches_search(_place("One Price Coffee", "food"), "кофе", "cafe")


def test_route_draft_blocklist_contains_non_tourist_categories_new() -> None:
    assert {"bank", "atm", "police", "mvd", "service", "transport", "pharmacy", "hospital"}.issubset(
        ROUTE_DRAFT_BLOCKED_CATEGORIES
    )
