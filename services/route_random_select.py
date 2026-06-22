from __future__ import annotations

import random

from models.place import Place
from models.route_draft import RouteDraft, RouteDraftPoint
from services.route_draft_quality import weighted_score
from services.route_draft_rules import target_points_for, visit_minutes_for


def select_random_places(candidates: list[Place], draft: RouteDraft, categories: list[str]) -> tuple[list[Place], bool]:
    target = target_points_for(draft.budget_minutes)
    if not candidates:
        return [], False
    rng = random.Random(draft.random_seed)
    ranked = sorted(candidates, key=lambda item: _score(item, draft, categories, rng), reverse=True)
    selected = _diverse_take(ranked, target)
    return (selected or ranked[: min(2, len(ranked))], not selected)


def point_for_place(place: Place, position: int) -> RouteDraftPoint:
    return RouteDraftPoint(place=place, place_id=place.id, position=position, visit_minutes=visit_minutes_for(place), open_status="unknown")


def _score(place: Place, draft: RouteDraft, categories: list[str], rng: random.Random) -> float:
    base = weighted_score(place, float(draft.start_lat or 0), float(draft.start_lng or 0), categories, draft.category_mode)
    return base * (0.8 + rng.random() * 0.4)


def _diverse_take(ranked: list[Place], target: int) -> list[Place]:
    selected: list[Place] = []
    category_counts: dict[str, int] = {}
    cap = max(1, (target + 1) // 2)
    for place in ranked:
        category = place.category or "unknown"
        selected_ids = {item.id for item in selected}
        alternatives = len({item.category for item in ranked if item.id not in selected_ids}) > 1
        if alternatives and category_counts.get(category, 0) >= cap:
            continue
        selected.append(place)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(selected) >= target:
            break
    return selected
