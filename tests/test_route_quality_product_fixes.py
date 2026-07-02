from __future__ import annotations

from types import SimpleNamespace

from services.place_coverage_route_score import route_features
from services.route_finalize_metrics import compute_distance
from services.route_user_warnings import route_warning_message, user_warnings
from tests.allure_support import title


@title("Route distance summary uses kilometer scale, not raw coordinate delta")
def test_route_distance_summary_uses_kilometer_scale() -> None:
    ctx = SimpleNamespace(location=(40.1792, 44.4991))
    route = [SimpleNamespace(lat=40.1850, lng=44.5100)]

    distance = compute_distance(route, ctx)  # type: ignore[arg-type]

    assert distance > 0.9
    assert distance < 2.0


@title("Route warning codes are mapped to user-facing text")
def test_route_warning_codes_are_mapped_to_user_facing_text() -> None:
    final = SimpleNamespace(warnings=["route_built_without_selected_interests", "neutral_poi_added"], places_with_warnings=[])

    warnings = user_warnings(final)

    assert all("_" not in str(item["user_message"]) for item in warnings)
    assert route_warning_message("route_budget_overflow_tolerated") == "Маршрут немного выходит за выбранное время."


@title("Inland cities do not get sea route feature from generic text")
def test_inland_cities_do_not_get_sea_route_feature_from_generic_text() -> None:
    places = [
        SimpleNamespace(category="promenade", title="River walk", short_description="Central walking place"),
        SimpleNamespace(category="museum", title="City museum", short_description="Culture"),
    ]

    assert route_features(places) == []  # type: ignore[arg-type]


@title("Explicit beach category enables sea route feature")
def test_explicit_beach_category_enables_sea_route_feature() -> None:
    places = [SimpleNamespace(category="beach", title="Beach", short_description="")]

    assert route_features(places) == ["sea"]  # type: ignore[arg-type]
