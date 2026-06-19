from __future__ import annotations

from services.route_interest_mapping import RULES, interest_match_score


def interest_exact_match(place: object, interests: list[str]) -> bool:
    cleaned = tuple(_norm(item) for item in interests if _norm(item))
    categories = _categories(place)
    return any(_exact_category_match(categories, interest) for interest in cleaned)


def interest_related_match(place: object, interests: list[str]) -> bool:
    return interest_match_score(place, interests) >= 0.6


def related_categories_for_interests(interests: list[str]) -> frozenset[str]:
    cleaned = {_norm(item) for item in interests if _norm(item)}
    direct = {item for item in cleaned if item}
    related = {
        category
        for rule in RULES
        if rule.aliases & cleaned
        for category, score in rule.categories.items()
        if score < 1.0
    }
    return frozenset(direct | related)


def _exact_category_match(categories: frozenset[str], interest: str) -> bool:
    direct = interest in categories
    semantic = any(_rule_exact_category_match(rule, categories) for rule in _matching_rules(interest))
    return direct or semantic


def _rule_exact_category_match(rule: object, categories: frozenset[str]) -> bool:
    pairs = getattr(rule, "categories", {}).items()
    return any(score >= 1.0 and category in categories for category, score in pairs)


def _matching_rules(interest: str) -> tuple[object, ...]:
    return tuple(rule for rule in RULES if interest in rule.aliases)


def _categories(place: object) -> frozenset[str]:
    raw = str(getattr(place, "category", "") or "")
    return frozenset(_norm(item) for item in raw.split(",") if _norm(item))


def _norm(value: str) -> str:
    return value.strip().casefold().replace("_", "-")
