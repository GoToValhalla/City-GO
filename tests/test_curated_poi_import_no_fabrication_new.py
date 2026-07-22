"""CITYGO-265: curated POI import must never fabricate a default visit
duration when a curated row omits it -- a human editor leaving the field
blank must result in NULL, not an invented "45 minutes" placeholder treated
as real evidence."""

from __future__ import annotations

from services.curated_poi_import_service import _curated_visit_duration


def test_missing_visit_duration_returns_none_new() -> None:
    assert _curated_visit_duration({}) is None


def test_null_visit_duration_returns_none_new() -> None:
    assert _curated_visit_duration({"average_visit_duration_minutes": None}) is None


def test_non_numeric_visit_duration_returns_none_new() -> None:
    assert _curated_visit_duration({"average_visit_duration_minutes": "unknown"}) is None


def test_boolean_visit_duration_returns_none_new() -> None:
    """isinstance(True, int) is True in Python -- must be explicitly rejected."""
    assert _curated_visit_duration({"average_visit_duration_minutes": True}) is None


def test_genuine_visit_duration_is_preserved_new() -> None:
    assert _curated_visit_duration({"average_visit_duration_minutes": 40}) == 40


def test_genuine_float_visit_duration_is_coerced_to_int_new() -> None:
    assert _curated_visit_duration({"average_visit_duration_minutes": 40.7}) == 40
