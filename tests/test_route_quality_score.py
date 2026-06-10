from services.route_assembly_service import RoutePoint
from services.route_quality_score import build_route_quality_score


def _point(
    category: str,
    opening_hours: dict[str, object] | None,
    price_level: int | None = 1,
) -> RoutePoint:
    return RoutePoint(
        place_id=category,
        lat=54.96,
        lng=20.48,
        score=0.8,
        category=category,
        visit_minutes=20,
        opening_hours=opening_hours,
        validation={"is_valid": True, "issues": []},
        price_level=price_level,
    )


def test_route_quality_score_rewards_balanced_complete_route() -> None:
    route = [_point("cafe", {"mon": None}), _point("museum", {"mon": None})]
    quality = build_route_quality_score(route, 2, 60, [])
    assert quality.score == 0.567
    assert quality.as_dict()["diversity"] == 1.0


def test_route_quality_score_penalizes_missing_data_and_warnings() -> None:
    route = [_point("cafe", None), _point("cafe", None)]
    quality = build_route_quality_score(route, 4, 30, ["warning"])
    assert quality.score < 0.75
    assert quality.diversity == 0.5
    assert quality.budget_fit < 1.0


def test_route_quality_score_marks_empty_route_as_zero() -> None:
    quality = build_route_quality_score([], 3, 60, ["empty"])
    assert quality.score == 0.0
    assert quality.warning_health == 0.92


def test_route_quality_score_caps_when_critical_data_is_missing() -> None:
    route = [_point("cafe", None, None), _point("museum", None, None)]
    quality = build_route_quality_score(route, 2, 60, [])
    assert quality.score == 0.567


def test_route_quality_score_penalizes_incomplete_route() -> None:
    quality = build_route_quality_score([_point("cafe", {"mon": None})], 4, 120, [])
    assert quality.completeness == 0.25
    assert quality.score < 0.4
