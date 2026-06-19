from __future__ import annotations

from statistics import mean
from typing import Any

from schemas.merged_context import MergedContext
from services.route_adaptive_types import RoutePlan
from services.route_interest_match import (
    interest_exact_match,
    interest_related_match,
    related_categories_for_interests,
)
from services.route_point_factory import visit_minutes_for_scored
from services.scoring_service import ScoredPlace


def prepare_route_plan(scored: list[ScoredPlace], ctx: MergedContext) -> RoutePlan:
    target = adaptive_target_points(scored, ctx)
    exact = [item for item in scored if interest_exact_match(item.place, list(ctx.interests))]
    related = [item for item in scored if item not in exact and interest_related_match(item.place, list(ctx.interests))]
    neutral = [item for item in scored if item not in exact and item not in related]
    level = _expansion_level(ctx, exact, related, neutral, target)
    ordered = _prioritized_scored(exact, related, neutral, level)
    warnings = _warnings(ctx, exact, related, neutral, level)
    return RoutePlan(
        scored=ordered,
        target_points=target,
        exact_count=len(exact),
        related_count=len(related),
        neutral_count=len(neutral),
        expansion_level=level,
        expanded_category_count=len(related_categories_for_interests(list(ctx.interests))),
        neutral_added_count=len(neutral) if level in {"neutral", "mixed"} else 0,
        warnings=warnings,
        user_explanation=_explanation(ctx, exact, related, neutral, level),
    )


def adaptive_target_points(scored: list[ScoredPlace], ctx: MergedContext) -> int:
    if not scored:
        return 0
    budget = int(ctx.effective_time_budget_minutes or ctx.time_budget_minutes or 0)
    visits = [visit_minutes_for_scored(item, ctx) for item in scored[:80]]
    avg_visit = max(12, int(mean(visits))) if visits else 25
    travel = 8 if len(scored) >= 30 else 12 if len(scored) >= 10 else 18
    pace_cap = 6 if str(ctx.pace_mode) == "slow" else 8
    by_budget = max(1, int(budget / max(1, avg_visit + travel)))
    short_cap = 2 if budget <= 75 else pace_cap
    return min(len(scored), max(1, min(short_cap, by_budget, pace_cap)))


def _prioritized_scored(
    exact: list[ScoredPlace], related: list[ScoredPlace], neutral: list[ScoredPlace], level: str
) -> list[ScoredPlace]:
    anchor_id = str(getattr(exact[0].place, "id", "")) if len(exact) == 1 else ""
    groups = (exact, related, neutral) if level != "primary" else (exact, related[:8], neutral[:8])
    return [_copy(item, _boost(item, anchor_id, kind)) for kind, group in zip(("primary", "related", "neutral"), groups) for item in group]


def _copy(item: ScoredPlace, data: dict[str, Any]) -> ScoredPlace:
    return ScoredPlace(item.place, data["score"], {**dict(item.breakdown or {}), **data["breakdown"]})


def _boost(item: ScoredPlace, anchor_id: str, kind: str) -> dict[str, Any]:
    delta = {"primary": 0.14, "related": 0.05, "neutral": -0.04}[kind]
    place_id = str(getattr(item.place, "id", ""))
    score = max(0.0, min(1.0, float(item.score) + delta))
    return {"score": score, "breakdown": {"route_match_type": kind, "route_anchor": 1.0 if place_id == anchor_id else 0.0}}


def _expansion_level(ctx: MergedContext, exact: list[ScoredPlace], related: list[ScoredPlace], neutral: list[ScoredPlace], target: int) -> str:
    if not ctx.interests:
        return "neutral"
    if len(exact) >= target:
        return "primary"
    if related and len(exact) + len(related) >= target:
        return "related"
    return "mixed" if neutral else "short"


def _warnings(ctx: MergedContext, exact: list[ScoredPlace], related: list[ScoredPlace], neutral: list[ScoredPlace], level: str) -> list[str]:
    return [
        *([] if ctx.interests else ["route_built_without_selected_interests"]),
        *(["selected_interests_have_no_exact_matches"] if ctx.interests and not exact else []),
        *(["selected_interest_has_single_anchor"] if len(exact) == 1 else []),
        *(["related_categories_added"] if level in {"related", "mixed"} and related else []),
        *(["neutral_poi_added"] if level in {"neutral", "mixed"} and neutral else []),
    ]


def _explanation(ctx: MergedContext, exact: list[ScoredPlace], related: list[ScoredPlace], neutral: list[ScoredPlace], level: str) -> str:
    if not ctx.interests:
        return "Маршрут собран по лучшим доступным точкам города без узкой привязки к интересам."
    if not exact and (related or neutral):
        return "Точных совпадений по интересам не нашлось, поэтому добавлены близкие категории и нейтральные точки."
    if len(exact) == 1:
        return "Найдено одно точное совпадение: оно использовано как якорь, остальные точки подобраны рядом."
    if level == "primary":
        return "Маршрут в основном собран из точек, совпадающих с выбранными интересами."
    return "Маршрут частично расширен за пределы точных интересов, чтобы сохранить полезный результат."
