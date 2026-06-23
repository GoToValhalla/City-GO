from __future__ import annotations

from pathlib import Path

import pytest

from core.place_category_hierarchy import (
    CATEGORY_LABELS_RU,
    ROUTE_EXCLUDED_CATEGORIES,
    normalize_category_code,
)
from core.place_taxonomy import PLACE_CATEGORIES


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pharmacy", "pharmacy"),
        ("clinic", "clinic"),
        ("hospital", "hospital"),
        ("health", "healthcare"),
        ("bank", "bank"),
        ("atm", "atm"),
        ("mall", "shopping_mall"),
        ("shopping_centre", "shopping_mall"),
        ("public_transport", "transport"),
        ("bus_stop", "bus_stop"),
        ("parking", "parking"),
    ],
)
def test_real_world_categories_are_not_collapsed_to_service_new(raw: str, expected: str) -> None:
    assert normalize_category_code(raw) == expected
    assert expected in PLACE_CATEGORIES
    assert expected in CATEGORY_LABELS_RU
    assert expected in ROUTE_EXCLUDED_CATEGORIES


def test_service_is_only_the_generic_fallback_new() -> None:
    assert normalize_category_code("service") == "service"
    assert normalize_category_code("services") == "service"
    assert CATEGORY_LABELS_RU["service"] == "Услуги"


def test_import_pipeline_executes_category_normalization_new() -> None:
    source = (ROOT / "services/import_pipeline_foundation_steps.py").read_text(encoding="utf-8")

    assert '"normalize_categories": lambda: _normalize_categories(db, places, counters)' in source
    assert '"normalize_categories": lambda: None' not in source
    assert "normalize_places_categories" in source


def test_verification_filters_are_url_backed_and_refresh_is_awaited_new() -> None:
    source = (ROOT / "frontend/src/pages/admin/AdminPlaceVerificationsPage.tsx").read_text(encoding="utf-8")

    assert "useSearchParams" in source
    assert "searchParams.get('city')" in source
    assert "searchParams.get('status')" in source
    assert "searchParams.get('category')" in source
    assert "searchParams.get('limit')" in source
    assert "await load(false)" in source
    assert "setTasks((current) => current.filter" in source
