from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from typing import List

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint
from services.route_quality_score import minimum_points_for_budget

ROUTE_BUDGET_TRIMMED_WARNING = "Route was trimmed to fit the selected time budget."
ROUTE_BUDGET_SINGLE_POINT_WARNING = "Even the first point may exceed the selected time budget."
ROUTE_BUDGET_UNDERFILLED_WARNING = "Route uses less than half of the selected time budget."


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

        if self._point_total_minutes(route[0]) > budget:
            return BudgetFitResult(
                route=[route[0]],
                warnings=[ROUTE_BUDGET_SINGLE_POINT_WARNING],
            )

        kept, dropped = self._fit_ordered_subset(route, budget)
        warnings: List[str] = []
        if dropped > 0:
            warnings.append(ROUTE_BUDGET_TRIMMED_WARNING)
        if kept and self._utilization(kept, budget) < 0.5 and len(route) >= minimum_points_for_budget(budget):
            if self._total_minutes(route) <= budget:
                kept = route
            warnings.append(ROUTE_BUDGET_UNDERFILLED_WARNING)
        return BudgetFitResult(route=kept, warnings=warnings)

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

    def _point_total_minutes(self, point: RoutePoint) -> int:
        walk = int(getattr(point, "estimated_walk_minutes", 0) or 0)
        visit = int(getattr(point, "visit_minutes", 0) or 0)
        return max(0, walk + visit)

    def _total_minutes(self, route: List[RoutePoint]) -> int:
        return sum(self._point_total_minutes(point) for point in route)

    def _utilization(self, route: List[RoutePoint], budget: int) -> float:
        return self._total_minutes(route) / max(1, budget)
