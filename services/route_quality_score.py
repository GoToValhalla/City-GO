from dataclasses import dataclass
from functools import reduce
from typing import Any, Literal

from services.route_quality_caps import minimum_data_cap

QualityStatus = Literal["good", "acceptable", "weak", "failed"]
_LONG_INITIAL_WALK_MINUTES = 20
_BUDGET_SWALLOWED_RATIO = 0.40


@dataclass(frozen=True)
class RouteQualityScore:
    score: float
    diversity: float
    budget_fit: float
    data_completeness: float
    warning_health: float
    completeness: float
    status: QualityStatus = "weak"
    minimum_points: int = 0
    actual_points: int = 0

    def as_dict(self) -> dict[str, float | str | int]:
        return dict(
            score=self.score,
            score_percent=int(round(self.score * 100)),
            status=self.status,
            diversity=self.diversity,
            budget_fit=self.budget_fit,
            data_completeness=self.data_completeness,
            warning_health=self.warning_health,
            completeness=self.completeness,
            minimum_points=self.minimum_points,
            actual_points=self.actual_points,
        )


def build_route_quality_score(
    route: list[Any],
    expected_stops: int,
    budget_minutes: int,
    warnings: list[str],
) -> RouteQualityScore:
    minimum_points = minimum_points_for_budget(budget_minutes)

    if not route:
        return RouteQualityScore(
            0.0,
            0.0,
            0.0,
            0.0,
            _warning_health(warnings),
            0.0,
            "failed",
            minimum_points,
            0,
        )

    diversity = _diversity_score(route, expected_stops)
    budget_fit = _budget_fit_score(route, budget_minutes)
    data_completeness = _data_completeness_score(route)
    completeness = _route_completeness_score(route, expected_stops, minimum_points)
    warning_health = _warning_health(warnings)
    raw_score = diversity * 0.25 + budget_fit * 0.15 + data_completeness * 0.35 + warning_health * 0.25
    score = min(_round_score(raw_score * completeness), minimum_data_cap(route))
    status = quality_status(score, route, budget_minutes)
    return RouteQualityScore(
        score,
        diversity,
        budget_fit,
        data_completeness,
        warning_health,
        completeness,
        status,
        minimum_points,
        len(route),
    )


def minimum_points_for_budget(budget_minutes: int) -> int:
    if budget_minutes < 75:
        return 1
    if budget_minutes < 150:
        return 2
    return 3


def quality_status(score: float, route: list[Any], budget_minutes: int) -> QualityStatus:
    if not route:
        return "failed"
    if any(not _has_coordinates(point) for point in route):
        return "failed"
    if budget_minutes >= 90 and len(route) <= 1:
        return "weak"
    if score >= 0.75:
        return "good"
    if score >= 0.50:
        return "acceptable"
    if score >= 0.25:
        return "weak"
    return "acceptable" if budget_minutes < 45 else "weak"


def public_quality_warnings(
    route: list[Any],
    budget_minutes: int,
    warnings: list[str] | None = None,
) -> list[str]:
    existing = list(warnings or [])
    result: list[str] = []

    if not route:
        return _unique([*existing, "route_failed_no_places"])

    if len(route) < minimum_points_for_budget(budget_minutes):
        result.append("route_short_due_to_time_budget" if budget_minutes < 45 else "route_short_due_to_low_place_density")

    if _has_long_initial_transfer(route):
        result.append("long_initial_transfer")
    if _budget_swallowed_by_transfer(route, budget_minutes):
        result.append("budget_swallowed_by_transfer")
    if any(not _has_address(point) for point in route):
        result.append("some_places_have_no_address")
    if any(not _has_image(point) for point in route):
        result.append("some_places_have_no_photo")
    if any(not _has_description(point) for point in route):
        result.append("some_places_have_weak_description")
    if any(int(getattr(point, "estimated_walk_minutes", 0) or 0) >= 18 for point in route):
        result.append("route_has_long_walk_segments")

    return _unique([*existing, *result])


def _diversity_score(route: list[Any], expected_stops: int) -> float:
    categories = set(map(lambda point: str(getattr(point, "category", "") or ""), route))
    target = max(1, min(len(route), expected_stops))
    return _round_score(min(1.0, len(categories) / target))


def _budget_fit_score(route: list[Any], budget_minutes: int) -> float:
    if budget_minutes <= 0: return 1.0
    total = reduce(lambda acc, point: acc + _point_minutes(point), route, 0)
    ratio = total / budget_minutes
    if 0.65 <= ratio <= 1.0: return 1.0
    if ratio < 0.65: return _round_score(max(0.0, ratio / 0.65))
    return _round_score(max(0.0, 1.0 - (ratio - 1.0)))


def _data_completeness_score(route: list[Any]) -> float:
    total = reduce(lambda acc, point: acc + _point_completeness(point), route, 0.0)
    return _round_score(total / max(1, len(route)))


def _route_completeness_score(route: list[Any], expected_stops: int, minimum_points: int) -> float:
    target = max(1, min(max(expected_stops, minimum_points), 8))
    return _round_score(min(1.0, len(route) / target))


def _warning_health(warnings: list[str]) -> float:
    unique = {str(item) for item in warnings if str(item).strip()}
    return _round_score(max(0.0, 1.0 - len(unique) * 0.08))


def _point_minutes(point: Any) -> int:
    walk = int(getattr(point, "estimated_walk_minutes", 0) or 0)
    visit = int(getattr(point, "visit_minutes", 0) or 0)
    return max(0, walk + visit)


def _point_completeness(point: Any) -> float:
    checks = (
        _has_coordinates(point),
        bool(str(getattr(point, "category", "") or "")),
        int(getattr(point, "visit_minutes", 0) or 0) > 0,
        _has_address(point),
        _has_image(point),
        _has_description(point),
        _has_valid_annotation(point),
    )
    passed = reduce(lambda acc, value: acc + (1 if value else 0), checks, 0)
    return passed / len(checks)


def _has_long_initial_transfer(route: list[Any]) -> bool:
    if not route:
        return False
    return int(getattr(route[0], "estimated_walk_minutes", 0) or 0) > _LONG_INITIAL_WALK_MINUTES


def _budget_swallowed_by_transfer(route: list[Any], budget_minutes: int) -> bool:
    if not route or budget_minutes <= 0:
        return False
    first_walk = int(getattr(route[0], "estimated_walk_minutes", 0) or 0)
    return (first_walk / max(1, budget_minutes)) > _BUDGET_SWALLOWED_RATIO


def _has_coordinates(point: Any) -> bool:
    return isinstance(point.lat, (int, float)) and isinstance(point.lng, (int, float))


def _has_address(point: Any) -> bool:
    return bool(str(getattr(point, "address", "") or "").strip())


def _has_image(point: Any) -> bool:
    return bool(str(getattr(point, "image_url", "") or "").strip())


def _has_description(point: Any) -> bool:
    return bool(str(getattr(point, "short_description", "") or "").strip())


def _has_valid_annotation(point: Any) -> bool:
    validation = getattr(point, "validation", None)
    if not isinstance(validation, dict):
        return True
    return bool(validation.get("is_valid", True))


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _round_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)
