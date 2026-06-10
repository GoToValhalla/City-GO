from types import SimpleNamespace

from services.route_quality_warnings import (
    DIVERSITY_WARNING,
    SHORT_ROUTE_WARNING,
    route_quality_warnings,
)


def _point(category: str):
    return SimpleNamespace(category=category)


def test_route_quality_warns_about_low_diversity() -> None:
    route = [_point("coffee"), _point("coffee"), _point("coffee")]
    assert route_quality_warnings(route, expected_stops=4) == [DIVERSITY_WARNING]


def test_route_quality_warns_about_short_route() -> None:
    route = [_point("coffee")]
    assert route_quality_warnings(route, expected_stops=5) == [SHORT_ROUTE_WARNING]


def test_route_quality_accepts_balanced_route() -> None:
    route = [_point("coffee"), _point("food"), _point("museum")]
    assert route_quality_warnings(route, expected_stops=4) == []
