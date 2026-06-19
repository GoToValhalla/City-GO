from __future__ import annotations

from dataclasses import dataclass

from services.route_adaptive_types import RoutePlan


@dataclass(frozen=True)
class QualityGateResult:
    route_quality_status: str
    route_completeness: float
    fallback_level: str
    warnings: list[str]
    partial_reason: str | None


def evaluate_quality_gates(
    route: list[object],
    plan: RoutePlan,
    diagnostics: dict[str, object],
    excluded_place_ids: list[str],
    avoided_categories: list[str],
    budget_reduced_to_zero: bool,
) -> QualityGateResult:
    completeness = _completeness(route, plan.target_points)
    warnings = [
        *(["algorithm_error_many_eligible_places_no_route"] if _many_eligible_no_route(route, diagnostics) else []),
        *(["selected_interests_have_no_exact_matches"] if plan.expansion_level in {"mixed", "short"} and plan.exact_count == 0 else []),
        *(["single_exact_match_anchor_not_included"] if _anchor_missing(route, plan) else []),
        *(["route_degraded_despite_expanded_pool"] if completeness < 0.3 and plan.expanded_pool_count >= 10 else []),
        *(["city_data_deficit_single_eligible_place"] if _eligible_count(diagnostics) == 1 else []),
        *(["budget_fit_reduced_route_to_zero"] if budget_reduced_to_zero else []),
        *(["route_violates_explicit_exclusions"] if _violates_exclusions(route, excluded_place_ids, avoided_categories) else []),
    ]
    status = _status(route, completeness, diagnostics, warnings)
    return QualityGateResult(
        route_quality_status=status,
        route_completeness=completeness,
        fallback_level=_fallback_level(plan),
        warnings=_unique([*plan.warnings, *warnings]),
        partial_reason=_partial_reason(status, warnings),
    )


def _status(route: list[object], completeness: float, diagnostics: dict[str, object], warnings: list[str]) -> str:
    if "route_violates_explicit_exclusions" in warnings:
        return "failed"
    if "algorithm_error_many_eligible_places_no_route" in warnings:
        return "algorithm_error"
    if not route:
        return "failed"
    if _eligible_count(diagnostics) == 1:
        return "single_point"
    if completeness >= 0.8:
        return "complete"
    if completeness >= 0.3:
        return "partial"
    return "degraded"


def _fallback_level(plan: RoutePlan) -> str:
    return {"primary": "none", "related": "related", "neutral": "neutral", "mixed": "neutral", "short": "short"}.get(
        plan.expansion_level, "unknown"
    )


def _partial_reason(status: str, warnings: list[str]) -> str | None:
    if status in {"complete", "single_point"}:
        return None
    return warnings[0] if warnings else "route_incomplete"


def _many_eligible_no_route(route: list[object], diagnostics: dict[str, object]) -> bool:
    return not route and _eligible_count(diagnostics) >= 100


def _eligible_count(diagnostics: dict[str, object]) -> int:
    value = diagnostics.get("places_route_eligible") or diagnostics.get("candidate_retrieval_city_wide_expected_count")
    return int(value) if isinstance(value, int) else 0


def _anchor_missing(route: list[object], plan: RoutePlan) -> bool:
    if plan.exact_count != 1:
        return False
    return not any(float(getattr(point, "scoring_breakdown", {}).get("route_anchor", 0.0) or 0.0) >= 1.0 for point in route)


def _violates_exclusions(route: list[object], excluded: list[str], avoided: list[str]) -> bool:
    excluded_ids = {str(item) for item in excluded}
    avoided_set = {str(item).casefold() for item in avoided}
    return any(str(getattr(point, "place_id", "")) in excluded_ids or str(getattr(point, "category", "")).casefold() in avoided_set for point in route)


def _completeness(route: list[object], target_points: int) -> float:
    return round(len(route) / max(1, target_points), 3) if target_points else 0.0


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
