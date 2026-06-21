from types import SimpleNamespace

from services.route_adaptive_types import RoutePlan
from services.route_quality_gates import evaluate_quality_gates


def _plan(target_points: int = 6, expanded_pool_count: int = 180) -> RoutePlan:
    scored = [SimpleNamespace() for _ in range(expanded_pool_count)]
    return RoutePlan(
        scored=scored,
        target_points=target_points,
        exact_count=0,
        related_count=0,
        neutral_count=expanded_pool_count,
        expansion_level="neutral",
        expanded_category_count=0,
        neutral_added_count=expanded_pool_count,
        warnings=[],
        user_explanation="",
    )


def _point(place_id: str = "1", category: str = "museum") -> SimpleNamespace:
    return SimpleNamespace(place_id=place_id, category=category, scoring_breakdown={})


def test_quality_gates_keep_single_anchor_as_non_failed_partial() -> None:
    result = evaluate_quality_gates(
        [_point()],
        _plan(),
        {"places_route_eligible": 159},
        [],
        [],
        False,
    )

    assert result.route_quality_status == "single_point"
    assert result.partial_reason == "not_enough_route_points"
    assert "algorithm_error_many_eligible_places_no_route" not in result.warnings


def test_quality_gates_keep_sparse_partial_route() -> None:
    result = evaluate_quality_gates(
        [_point("1"), _point("2", "park")],
        _plan(target_points=6),
        {"places_route_eligible": 159},
        [],
        [],
        False,
    )

    assert result.route_quality_status == "partial"
    assert result.partial_reason != "algorithm_error_many_eligible_places_no_route"
