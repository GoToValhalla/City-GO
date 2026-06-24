"""Централизованная политика допуска категорий в маршруты."""

from __future__ import annotations

from dataclasses import dataclass

from models.category import Category

ROUTE_CONTEXTS = frozenset({"tourist_walk", "family", "food", "coffee", "practical", "emergency", "accessibility"})
ROUTE_POLICIES = frozenset({"always_allowed", "allowed_by_context", "useful_only", "forbidden", "manual_review"})


@dataclass(frozen=True, slots=True)
class RoutePolicyDecision:
    allowed: bool
    requires_review: bool
    reason: str


def evaluate_category_policy(category: Category | None, *, context: str = "tourist_walk") -> RoutePolicyDecision:
    if category is None or not category.is_active:
        return RoutePolicyDecision(False, True, "Категория отсутствует или архивирована.")
    if context not in ROUTE_CONTEXTS:
        return RoutePolicyDecision(False, True, "Неизвестный контекст маршрута.")

    policy = category.route_policy or "manual_review"
    if policy == "always_allowed":
        return RoutePolicyDecision(True, False, "Категория разрешена во всех маршрутах.")
    if policy == "forbidden":
        return RoutePolicyDecision(False, False, "Категория запрещена политикой маршрутов.")
    if policy == "manual_review":
        return RoutePolicyDecision(False, True, "Категория требует ручной проверки.")
    if policy == "useful_only":
        allowed = context in {"practical", "emergency", "accessibility"}
        return RoutePolicyDecision(allowed, False, "Инфраструктура разрешена только в практическом контексте.")

    allowed_contexts = set(category.route_contexts or [])
    allowed = context in allowed_contexts
    return RoutePolicyDecision(allowed, False, "Контекст разрешён категорией." if allowed else "Контекст не разрешён категорией.")
