from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import List

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint
from services.route_quality_score import minimum_points_for_budget

ROUTE_BUDGET_TRIMMED_WARNING = "route_trimmed_by_budget"
ROUTE_BUDGET_SINGLE_POINT_WARNING = "budget_very_tight"
ROUTE_BUDGET_TOO_TIGHT_WARNING = "budget_too_tight"
ROUTE_BUDGET_UNDERFILLED_WARNING = "route_underfilled_by_budget"
ROUTE_LOW_DENSITY_SHORT_WARNING = "route_short_due_to_low_place_density"
_TIGHT_BUDGET_MINUTES = 75
_LOW_UTILIZATION_RATIO = 0.5


@dataclass(frozen=True)
class BudgetFitResult:
    route: List[RoutePoint]
    warnings: List[str]


class RouteBudgetFitService:
    def fit(self, route: List[RoutePoint], ctx: MergedContext) -> BudgetFitResult:
        if not route:
            return BudgetFitResult(route=[], warnings=[])

        budget = max(0, int(ctx.effective_time_budget_minutes or ctx.time_budget_minutes or 0))
        if budget <= 0:
            return BudgetFitResult(route=route, warnings=[])

        first_total = self._point_total_minutes(route[0])
        if first_total > budget:
            return BudgetFitResult(
                route=[route[0]],
                warnings=[self._short_route_warning(budget)],
            )

        kept, dropped = self._fit_ordered_subset(route, budget)
        if not kept:
            return BudgetFitResult(route=[route[0]], warnings=["budget_fit_recovered_first_point"])

        warnings: List[str] = []
        if dropped > 0:
            warnings.append(ROUTE_BUDGET_TRIMMED_WARNING)
        if len(kept) < minimum_points_for_budget(budget):
            warnings.append(self._short_route_warning(budget))
        if self._utilization(kept, budget) < _LOW_UTILIZATION_RATIO and len(route) >= minimum_points_for_budget(budget):
            if self._total_minutes(route) <= budget:
                kept = route
            warnings.append(ROUTE_BUDGET_UNDERFILLED_WARNING)
        return BudgetFitResult(route=kept, warnings=list(dict.fromkeys(warnings)))

    def _fit_ordered_subset(
        self,
        route: List[RoutePoint],
        budget: int,
    ) -> tuple[List[RoutePoint], int]:
        state = ([], 0, 0)
        kept, _total, dropped = reduce(
            lambda acc, point: self._append_if_fits(acc, point, budget),
            route,
            state,
        )
        return kept, dropped

    def _append_if_fits(
        self,
        state: tuple[List[RoutePoint], int, int],
        point: RoutePoint,
        budget: int,
    ) -> tuple[List[RoutePoint], int, int]:
        kept, total, dropped = state
        point_minutes = self._point_total_minutes(point)
        fits = total + point_minutes <= budget
        if fits:
            return [*kept, point], total + point_minutes, dropped
        return kept, total, dropped + 1

    def _short_route_warning(self, budget: int) -> str:
        return ROUTE_BUDGET_SINGLE_POINT_WARNING if budget < _TIGHT_BUDGET_MINUTES else ROUTE_LOW_DENSITY_SHORT_WARNING

    def _point_total_minutes(self, point: RoutePoint) -> int:
        walk = int(getattr(point, "estimated_walk_minutes", 0) or 0)
        visit = int(getattr(point, "visit_minutes", 0) or 0)
        return max(0, walk + visit)

    def _total_minutes(self, route: List[RoutePoint]) -> int:
        return sum(self._point_total_minutes(point) for point in route)

    def _utilization(self, route: List[RoutePoint], budget: int) -> float:
        return self._total_minutes(route) / max(1, budget)
