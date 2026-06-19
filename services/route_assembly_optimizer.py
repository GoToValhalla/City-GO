from __future__ import annotations

from dataclasses import dataclass

from schemas.merged_context import MergedContext
from services.route_diversity_policy import add_category, can_use_category, normalize_category
from services.route_geometry import walk_minutes_between
from services.route_point_factory import route_point_from_scored, visit_minutes_for_scored
from services.route_quality_score import minimum_points_for_budget
from services.route_walk_annotations import annotate_walks
from services.scoring_service import ScoredPlace

# Минимальная продуктовая утилизация бюджета при достаточном пуле кандидатов.
MIN_BUDGET_UTILIZATION = 0.65
# Выше этого значения маршрут уже считается достаточно наполненным и не добирается любой ценой.
TARGET_BUDGET_UTILIZATION = 0.86
# Базовая длительность точки для расчёта целевого количества остановок.
DEFAULT_MINUTES_PER_POINT = 30
MAX_TARGET_POINTS = 8
MAX_RELAXATION_STAGE = 3
# Ограничение на один пеший переход: раньше дальняя первая точка съедала почти весь бюджет.
STRICT_MAX_WALK_MINUTES = 35
RELAXED_MAX_WALK_MINUTES = 55
WALK_INTERESTS = {"walk", "park", "outdoor", "sea"}
WALK_ROUTE_CATEGORIES = {
    "walk",
    "park",
    "outdoor",
    "attraction",
    "culture",
    "coffee",
    "cafe",
    "museum",
    "gallery",
    "historic",
    "history",
    "landmark",
    "monument",
    "promenade",
    "sightseeing",
    "viewpoint",
    "food",
    "restaurant",
}


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
    """Build a route that prioritizes product usefulness over premature strictness.

    The old implementation could stop after one or two high-score but distant points.
    This version still starts with scored candidates, then explicitly backfills by proximity
    and relaxes diversity limits until the route reaches a reasonable point count or budget use.
    """

    if not scored:
        return []

    lat, lng = ctx.location
    budget = _assembly_budget(ctx)
    target_points = _target_points(ctx, budget)
    candidate_pool = scored[:160]

    state = AssemblyState([], budget, lat, lng, {}, candidate_pool, target_points)
    route = _select_until_done(state, ctx, point_cls)

    if _needs_time_fill(route, budget, target_points):
        route = _fill_remaining_time(route, candidate_pool, ctx, point_cls, budget, target_points)

    if _needs_time_fill(route, budget, target_points):
        route = _greedy_proximity_backfill(route, candidate_pool, ctx, point_cls, budget, target_points)

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
    # Не останавливаемся только потому, что уже набрали пару точек: сначала target_points
    # или реальное исчерпание бюджета.
    return len(state.route) >= state.target_points or state.remaining <= ctx.min_stop_duration_minutes


def _best_candidate(state: AssemblyState, ctx: MergedContext) -> ScoredPlace | None:
    feasible = tuple(filter(lambda item: _fits(item, state, ctx), state.candidates))
    return max(feasible, key=lambda item: _assembly_score(item, state, ctx), default=None)


def _fits(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> bool:
    category = str(getattr(scored.place, "category", "") or "")
    category_ok = _can_use_category_for_route(category, state.used_categories, state.relaxation_stage, len(state.route), ctx)
    if not category_ok:
        return False

    total_minutes = _total_minutes(scored, state, ctx)
    if total_minutes > state.remaining:
        return False

    # Защита от маршрутов, где одна дальняя точка съедает весь бюджет.
    walk = walk_minutes_between(state.lat, state.lng, float(scored.place.lat), float(scored.place.lng))
    return walk <= _max_walk_minutes_for_stage(state.relaxation_stage)


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
    if route_len >= min_points and relaxation_stage < MAX_RELAXATION_STAGE:
        return _can_use_category_for_route(category, used, 0, route_len, ctx)

    base_limit = 4 if (_is_walking_route(ctx) and normalized in WALK_ROUTE_CATEGORIES) else 3
    bonus = relaxation_stage
    return used.get(normalized, 0) < base_limit + bonus


def _relax_state(state: AssemblyState, ctx: MergedContext) -> AssemblyState | None:
    min_points = minimum_points_for_budget(_assembly_budget(ctx))
    underfilled = len(state.route) < max(min_points, min(5, state.target_points))
    if underfilled and state.relaxation_stage < MAX_RELAXATION_STAGE:
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
    proximity_bonus = _proximity_bonus(scored, state)
    return (
        float(scored.score) * 0.42
        + min(1.0, value_per_minute * 24.0) * 0.24
        + interest * 0.12
        + route_fit * 0.10
        + proximity_bonus * 0.18
        - diversity_penalty
    )


def _proximity_bonus(scored: ScoredPlace, state: AssemblyState) -> float:
    walk = walk_minutes_between(state.lat, state.lng, float(scored.place.lat), float(scored.place.lng))
    if walk <= 8:
        return 1.0
    if walk <= 18:
        return 0.75
    if walk <= 30:
        return 0.45
    if walk <= 45:
        return 0.22
    return 0.0


def _category_pressure(scored: ScoredPlace, state: AssemblyState) -> float:
    category = normalize_category(getattr(scored.place, "category", ""))
    if not category:
        return 0.0
    return min(0.22, state.used_categories.get(category, 0) * 0.06)


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

    while len(current) < target_points and _route_minutes(current) < int(budget * TARGET_BUDGET_UTILIZATION):
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


def _greedy_proximity_backfill(
    route: list[object],
    scored: list[ScoredPlace],
    ctx: MergedContext,
    point_cls: type,
    budget: int,
    target_points: int,
) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    min_points = min(minimum_points_for_budget(budget), target_points)

    while len(current) < target_points and _route_minutes(current) < int(budget * TARGET_BUDGET_UTILIZATION):
        lat, lng = _tail_location(current, ctx)
        remaining = budget - _route_minutes(current)
        if remaining <= ctx.min_stop_duration_minutes:
            break

        candidates = [item for item in scored if str(getattr(item.place, "id", "")) not in used_ids]
        selected = _nearest_feasible_candidate(candidates, lat, lng, remaining, ctx, require_close=len(current) >= min_points)
        if selected is None:
            break

        point = route_point_from_scored(selected, ctx, point_cls)
        point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
        current.append(point)
        used_ids.add(str(getattr(point, "place_id", "")))

    return current


def _nearest_feasible_candidate(
    candidates: list[ScoredPlace],
    lat: float,
    lng: float,
    remaining: int,
    ctx: MergedContext,
    require_close: bool,
) -> ScoredPlace | None:
    feasible = []
    for item in candidates:
        walk = walk_minutes_between(lat, lng, float(item.place.lat), float(item.place.lng))
        total = walk + visit_minutes_for_scored(item, ctx)
        max_walk = STRICT_MAX_WALK_MINUTES if require_close else RELAXED_MAX_WALK_MINUTES
        if total <= remaining and walk <= max_walk:
            feasible.append((walk, -float(item.score), item))
    feasible.sort(key=lambda item: (item[0], item[1]))
    return feasible[0][2] if feasible else None


def _fill_stage(route: list[object], budget: int) -> int:
    if len(route) < minimum_points_for_budget(budget):
        return MAX_RELAXATION_STAGE
    return 1


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


def _max_walk_minutes_for_stage(stage: int) -> int:
    if stage <= 0:
        return STRICT_MAX_WALK_MINUTES
    if stage >= MAX_RELAXATION_STAGE:
        return RELAXED_MAX_WALK_MINUTES
    return STRICT_MAX_WALK_MINUTES + (stage * 8)
