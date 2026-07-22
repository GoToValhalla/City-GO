"""CITYGO-265: base_quality_score must reward genuine data only.

Before this fix, average_visit_duration_minutes was fabricated from a
per-category lookup table at import time (data/scripts/import_city_osm.py's
former _visit_duration()), so _has_visit_duration() -- and therefore 20% of
base_quality_score -- was unconditionally True for every imported place,
regardless of whether the value reflected anything real about that place.
These tests pin the scoring function's own contract (a positive numeric
duration scores 0.2, anything else scores 0.0) so a future reintroduction of
a fabricated default is caught here even if the generator itself is gone.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.route_base_quality_score import base_quality_score


def _place(**overrides) -> SimpleNamespace:
    base = {
        "lat": 54.9,
        "lng": 20.5,
        "opening_hours": {"mon": {"open": "09:00", "close": "18:00"}},
        "average_visit_duration_minutes": None,
        "image_url": "https://example.com/photo.jpg",
        "image": None,
        "short_description": "Реальное описание места",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_missing_visit_duration_contributes_nothing_new() -> None:
    without = base_quality_score(_place(average_visit_duration_minutes=None))
    with_duration = base_quality_score(_place(average_visit_duration_minutes=45))

    assert round(with_duration - without, 6) == 0.2


def test_zero_visit_duration_does_not_score_as_present_new() -> None:
    """A falsy-but-present value (0) must not count as "has a duration" --
    only a genuine positive number does."""
    assert base_quality_score(_place(average_visit_duration_minutes=0)) == base_quality_score(_place(average_visit_duration_minutes=None))


def test_negative_visit_duration_does_not_score_as_present_new() -> None:
    assert base_quality_score(_place(average_visit_duration_minutes=-10)) == base_quality_score(_place(average_visit_duration_minutes=None))


def test_boolean_visit_duration_is_not_treated_as_numeric_new() -> None:
    """isinstance(True, int) is True in Python -- the scoring function must
    explicitly reject bool, not just check isinstance(value, (int, float))."""
    assert base_quality_score(_place(average_visit_duration_minutes=True)) == base_quality_score(_place(average_visit_duration_minutes=None))


def test_genuine_positive_visit_duration_scores_present_new() -> None:
    score = base_quality_score(_place(average_visit_duration_minutes=45))
    baseline = base_quality_score(_place(average_visit_duration_minutes=None))

    assert score > baseline


def test_score_is_bounded_between_zero_and_one_new() -> None:
    minimal = _place(lat=None, lng=None, opening_hours=None, average_visit_duration_minutes=None, image_url=None, short_description=None)
    maximal = _place(average_visit_duration_minutes=45)

    assert 0.0 <= base_quality_score(minimal) <= 1.0
    assert 0.0 <= base_quality_score(maximal) <= 1.0
