from __future__ import annotations

from dataclasses import dataclass

from schemas.merged_context import MergedContext
from services.route_diversity_policy import add_category, can_use_category, normalize_category
from services.route_geometry import walk_minutes_between
from services.route_point_factory import route_point_from_scored, visit_minutes_for_scored
from services.route_quality_score import minimum_points_for_budget
from services.route_walk_annotations import annotate_walks
from services.scoring_service import ScoredPlace

MIN_BUDGET_UTILIZATION = 0.78
DEFAULT_MINUTES_PER_POINT = 24
MAX_TARGET_POINTS = 8
MAX_RELAXATION_STAGE = 2
WALK_INTERESTS = {"walk", "park", "outdoor", "sea"}
WALK_ROUTE_CATEGORIES = {"walk", "park", "outdoor", "attraction", "culture", "coffee", "cafe"}


@dataclass(frozen=True)
class AssemblyState:
    route: list[object]
    remaining: int
    lat: float
    lng: float
    used_categories: dict[str, int]
    candidates: list[ScoredPlace]
    target_points: int
    relaxed_budget: bool = False
    relaxation_stage: int = 0


def assemble_route(scored: list[ScoredPlace], ctx: MergedContext, point_cls: type) -> list[object]:
    lat, lng = ctx.location
    budget = _assembly_budget(ctx)
    target_points = _target_points(ctx, budget)
    state = AssemblyState([], budget, lat, lng, {}, scored[:120], target_points)
    route = _select_until_done(state, ctx, point_cls)
    if _needs_time_fill(route, budget, target_points):
        route = _fill_remaining_time(route, scored[:120], ctx, point_cls, budget, target_points)
    return annotate_walks(_cleanup_loops(route), ctx.location)


def _select_until_done(state: AssemblyState, ctx: MergedContext, point_cls: type) -> list[object]:
    if _done(state, ctx):
        return state.route

    selected = _best_candidate(state, ctx)
    if selected is None:
        relaxed = _relax_state(state, ctx)
        if relaxed is None:
            return state.route
        selected = _best_candidate(relaxed, ctx)
        if selected is None:
            return state.route
        state = relaxed

    point = route_point_from_scored(selected, ctx, point_cls)
    walk = walk_minutes_between(state.lat, state.lng, point.lat, point.lng)
    point.estimated_walk_minutes = walk
    return _select_until_done(_next_state(state, selected, point, walk), ctx, point_cls)


def _done(state: AssemblyState, ctx: MergedContext) -> bool:
    return len(state.route) >= state.target_points or state.remaining <= ctx.min_stop_duration_minutes


def _best_candidate(state: AssemblyState, ctx: MergedContext) -> ScoredPlace | None:
    feasible = tuple(filter(lambda item: _fits(item, state, ctx), state.candidates))
    return max(feasible, key=lambda item: _assembly_score(item, state, ctx), default=None)


def _fits(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> bool:
    category = str(getattr(scored.place, "category", "") or "")
    category_ok = _can_use_category_for_route(category, state.used_categories, state.relaxation_stage, len(state.route), ctx)
    return category_ok and _total_minutes(scored, state, ctx) <= state.remaining


def _can_use_category_for_route(
    category: str,
    used: dict[str, int],
    relaxation_stage: int,
    route_len: int,
    ctx: MergedContext,
) -> bool:
    normalized = normalize_category(category)
    if not normalized:
        return can_use_category(category, used)

    if relaxation_stage <= 0:
        if _is_walking_route(ctx) and normalized in WALK_ROUTE_CATEGORIES:
            return used.get(normalized, 0) < 3
        return can_use_category(category, used)

    min_points = minimum_points_for_budget(_assembly_budget(ctx))
    if route_len >= min_points:
        return _can_use_category_for_route(category, used, 0, route_len, ctx)

    base_limit = 3 if (_is_walking_route(ctx) and normalized in WALK_ROUTE_CATEGORIES) else 2
    bonus = 1 if relaxation_stage >= 1 and normalized in WALK_ROUTE_CATEGORIES else 0
    bonus += 1 if relaxation_stage >= 2 and normalized not in WALK_ROUTE_CATEGORIES else 0
    return used.get(normalized, 0) < base_limit + bonus


def _relax_state(state: AssemblyState, ctx: MergedContext) -> AssemblyState | None:
    min_points = minimum_points_for_budget(_assembly_budget(ctx))
    if len(state.route) < min_points and state.relaxation_stage < MAX_RELAXATION_STAGE:
        return AssemblyState(
            route=state.route,
            remaining=state.remaining,
            lat=state.lat,
            lng=state.lng,
            used_categories=state.used_categories,
            candidates=state.candidates,
            target_points=state.target_points,
            relaxed_budget=state.relaxed_budget,
            relaxation_stage=state.relaxation_stage + 1,
        )

    if not state.relaxed_budget and len(state.route) == 0:
        extra = _assembly_budget(ctx)
        target_budget = max(state.remaining, int(extra * 1.1))
        return AssemblyState(
            route=state.route,
            remaining=target_budget,
            lat=state.lat,
            lng=state.lng,
            used_categories=state.used_categories,
            candidates=state.candidates,
            target_points=state.target_points,
            relaxed_budget=True,
            relaxation_stage=min(MAX_RELAXATION_STAGE, state.relaxation_stage + 1),
        )

    return None


def _total_minutes(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> int:
    place = scored.place
    walk = walk_minutes_between(state.lat, state.lng, float(place.lat), float(place.lng))
    return walk + visit_minutes_for_scored(scored, ctx)


def _assembly_score(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> float:
    total = max(1, _total_minutes(scored, state, ctx))
    value_per_minute = float(scored.score) / total
    interest = float(scored.breakdown.get("interest", 0.0)) if isinstance(scored.breakdown, dict) else 0.0
    route_fit = _walk_route_fit(scored, ctx)
    diversity_penalty = _category_pressure(scored, state)
    return float(scored.score) * 0.5 + min(1.0, value_per_minute * 20.0) * 0.25 + interest * 0.15 + route_fit * 0.1 - diversity_penalty


def _category_pressure(scored: ScoredPlace, state: AssemblyState) -> float:
    category = normalize_category(getattr(scored.place, "category", ""))
    if not category:
        return 0.0
    return min(0.25, state.used_categories.get(category, 0) * 0.08)


def _next_state(state: AssemblyState, selected: ScoredPlace, point: object, walk: int) -> AssemblyState:
    left = [item for item in state.candidates if item is not selected]
    spent = walk + int(getattr(point, "visit_minutes", 0) or 0)
    used = add_category(str(getattr(point, "category", "") or ""), state.used_categories)
    return AssemblyState(
        [*state.route, point],
        state.remaining - spent,
        point.lat,
        point.lng,
        used,
        left,
        state.target_points,
        state.relaxed_budget,
        state.relaxation_stage,
    )


def _needs_time_fill(route: list[object], budget: int, target_points: int) -> bool:
    if not route:
        return False
    if len(route) < min(minimum_points_for_budget(budget), target_points):
        return True
    return len(route) < target_points and _route_minutes(route) < int(budget * MIN_BUDGET_UTILIZATION)


def _fill_remaining_time(
    route: list[object],
    scored: list[ScoredPlace],
    ctx: MergedContext,
    point_cls: type,
    budget: int,
    target_points: int,
) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    used_categories: dict[str, int] = {}
    for point in current:
        used_categories = add_category(str(getattr(point, "category", "") or ""), used_categories)

    while len(current) < target_points:
        lat, lng = _tail_location(current, ctx)
        remaining = budget - _route_minutes(current)
        if remaining <= ctx.min_stop_duration_minutes:
            break
        candidates = [item for item in scored if str(getattr(item.place, "id", "")) not in used_ids]
        stage = _fill_stage(current, budget)
        state = AssemblyState(current, remaining, lat, lng, used_categories, candidates, target_points, relaxation_stage=stage)
        selected = _best_candidate(state, ctx)
        if selected is None:
            break
        point = route_point_from_scored(selected, ctx, point_cls)
        point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
        current.append(point)
        used_ids.add(str(getattr(point, "place_id", "")))
        used_categories = add_category(str(getattr(point, "category", "") or ""), used_categories)
    return current


def _fill_stage(route: list[object], budget: int) -> int:
    return 1 if len(route) < minimum_points_for_budget(budget) else 0


def _tail_location(route: list[object], ctx: MergedContext) -> tuple[float, float]:
    if route:
        last = route[-1]
        return float(getattr(last, "lat")), float(getattr(last, "lng"))
    return ctx.location


def _route_minutes(route: list[object]) -> int:
    return sum(int(getattr(point, "visit_minutes", 0) or 0) + int(getattr(point, "estimated_walk_minutes", 0) or 0) for point in route)


def _target_points(ctx: MergedContext, budget: int) -> int:
    from_context = int(getattr(ctx, "effective_num_stops", 0) or 0)
    by_budget = max(minimum_points_for_budget(budget), int(budget / DEFAULT_MINUTES_PER_POINT))
    if _is_walking_route(ctx):
        by_budget = max(4, by_budget)
    return max(minimum_points_for_budget(budget), min(MAX_TARGET_POINTS, max(from_context, by_budget)))


def _is_walking_route(ctx: MergedContext) -> bool:
    interests = {str(item).strip().casefold() for item in getattr(ctx, "interests", []) or []}
    return not interests or bool(interests & WALK_INTERESTS)


def _walk_route_fit(scored: ScoredPlace, ctx: MergedContext) -> float:
    category = str(getattr(scored.place, "category", "") or "").strip().casefold()
    return 1.0 if _is_walking_route(ctx) and category in WALK_ROUTE_CATEGORIES else 0.0


def _cleanup_loops(route: list[object]) -> list[object]:
    if len(route) < 3:
        return route
    first, second, third, *tail = route
    return _cleanup_loops([first, third, second, *tail]) if _swap_shortens(first, second, third) else [first, *_cleanup_loops([second, third, *tail])]


def _swap_shortens(first: object, second: object, third: object) -> bool:
    current = walk_minutes_between(first.lat, first.lng, second.lat, second.lng)
    swapped = walk_minutes_between(first.lat, first.lng, third.lat, third.lng)
    return swapped < current


def _assembly_budget(ctx: MergedContext) -> int:
    effective = int(getattr(ctx, "effective_time_budget_minutes", 0) or 0)
    explicit = int(getattr(ctx, "time_budget_minutes", 0) or 0)
    return effective or int(explicit * 0.9)
