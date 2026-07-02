"""Централизованная политика допуска категорий в маршруты."""

from __future__ import annotations

from dataclasses import dataclass

from models.category import Category
from services.route_diversity_policy import normalize_category

ROUTE_CONTEXTS = frozenset({"tourist_walk", "family", "food", "coffee", "practical", "emergency", "accessibility"})
ROUTE_POLICIES = frozenset({"always_allowed", "allowed_by_context", "useful_only", "forbidden", "manual_review"})
ALWAYS = frozenset({"museum", "walk", "park", "culture", "history", "landmark", "viewpoint"})
CONTEXTUAL = frozenset({"cafe", "food", "restaurant", "bar", "shopping"})
USEFUL = frozenset({"health", "service", "utility", "transport"})
FORBIDDEN = frozenset({"hospital", "police", "shelter", "unknown"})
KNOWN = ALWAYS | CONTEXTUAL | USEFUL | FORBIDDEN


@dataclass(frozen=True, slots=True)
class RoutePolicyDecision:
    allowed: bool
    requires_review: bool
    reason: str


def evaluate_category_policy(
    category: Category | None,
    *,
    context: str = "tourist_walk",
    fallback_code: str | None = None,
) -> RoutePolicyDecision:
    if context not in ROUTE_CONTEXTS:
        return RoutePolicyDecision(False, True, "Неизвестный контекст маршрута.")
    if category is None:
        return evaluate_category_code_policy(fallback_code, context=context)
    if not category.is_active:
        return RoutePolicyDecision(False, True, "Категория архивирована.")
    code = normalize_category(category.code)
    policy = category.route_policy or "manual_review"
    if policy == "manual_review" and code in KNOWN:
        return evaluate_category_code_policy(code, context=context)
    if policy == "always_allowed":
        return RoutePolicyDecision(True, False, "Категория разрешена во всех маршрутах.")
    if policy == "forbidden":
        return RoutePolicyDecision(False, False, "Категория запрещена политикой маршрутов.")
    if policy == "manual_review":
        return RoutePolicyDecision(False, True, "Категория требует ручной проверки.")
    if policy == "useful_only":
        return RoutePolicyDecision(context in {"practical", "emergency", "accessibility"}, False, "Инфраструктура разрешена только в практическом контексте.")
    contexts = set(category.route_contexts or []) or _default_contexts(code)
    return RoutePolicyDecision(context in contexts, False, "Контекст разрешён категорией." if context in contexts else "Контекст не разрешён категорией.")


def evaluate_category_code_policy(code: str | None, *, context: str = "tourist_walk") -> RoutePolicyDecision:
    value = normalize_category(code)
    if value in ALWAYS:
        return RoutePolicyDecision(True, False, "Категория разрешена централизованной политикой.")
    if value in CONTEXTUAL:
        if value == "shopping":
            return RoutePolicyDecision(False, True, "ТЦ/магазины требуют явной туристической причины перед маршрутом.")
        return RoutePolicyDecision(context in {"tourist_walk", "family", "food", "coffee"}, False, "Сценарная категория проверена централизованной политикой.")
    if value in USEFUL:
        return RoutePolicyDecision(context in {"practical", "emergency", "accessibility"}, False, "Инфраструктурная категория разрешена только в практическом контексте.")
    if value in FORBIDDEN:
        return RoutePolicyDecision(False, False, "Категория запрещена централизованной политикой.")
    return RoutePolicyDecision(False, True, "Категория отсутствует или требует ручной проверки.")


def _default_contexts(code: str) -> set[str]:
    value = normalize_category(code)
    if value == "cafe":
        return {"tourist_walk", "family", "coffee", "food"}
    if value in {"food", "restaurant", "bar"}:
        return {"tourist_walk", "family", "food"}
    return {"tourist_walk"}
