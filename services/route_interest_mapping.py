from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InterestRule:
    aliases: frozenset[str]
    categories: dict[str, float]
    tags: frozenset[str] = frozenset()


RULES: tuple[InterestRule, ...] = (
    InterestRule(frozenset({"архитектура", "история", "historic", "architecture"}),
                 {"culture": 1.0, "museum": 1.0, "walk": 0.78}),
    InterestRule(frozenset({"еда", "есть", "food", "restaurant"}),
                 {"food": 1.0, "restaurant": 1.0, "coffee": 0.78, "cafe": 0.78}),
    InterestRule(frozenset({"кофе", "coffee", "cafe"}), {"coffee": 1.0, "cafe": 1.0, "food": 0.62}),
    InterestRule(frozenset({"природа", "nature", "walk", "quiet"}),
                 {"park": 1.0, "walk": 0.92, "outdoor": 0.85}),
    InterestRule(frozenset({"море", "sea"}),
                 {"sea": 1.0, "beach": 1.0, "waterfront": 1.0, "coast": 1.0, "promenade": 0.9}),
    InterestRule(frozenset({"активный отдых", "active", "sport"}),
                 {"walk": 1.0, "outdoor": 0.9, "dog-friendly": 0.7}),
    InterestRule(frozenset({"вечер", "evening", "bar", "night"}),
                 {"evening": 1.0, "bar": 1.0, "food": 0.82}),
    InterestRule(frozenset({"семья", "дети", "family", "kids"}),
                 {"family": 1.0, "park": 0.82, "indoor": 0.72}),
)


def interest_match_score(place: object, interests: list[str]) -> float:
    cleaned = tuple(_norm(item) for item in interests if _norm(item))
    if not cleaned:
        return 0.5
    category_scores = [_category_score(_categories(place), interest) for interest in cleaned]
    tag_scores = [_tag_score(_tags(place), interest) for interest in cleaned]
    return max([0.0, *category_scores, *tag_scores])


def interest_coverage(place: object, interests: list[str]) -> bool:
    return interest_match_score(place, interests) >= 0.6


def _category_score(categories: frozenset[str], interest: str) -> float:
    direct = 1.0 if interest in categories else 0.0
    semantic = max([_rule_category_score(rule, categories) for rule in _matching_rules(interest)] or [0.0])
    fuzzy = max([0.72 if _fuzzy(interest, category) else 0.0 for category in categories] or [0.0])
    return max(direct, semantic, fuzzy)


def _rule_category_score(rule: InterestRule, categories: frozenset[str]) -> float:
    return max([score for category, score in rule.categories.items() if category in categories] or [0.0])


def _tag_score(tags: frozenset[str], interest: str) -> float:
    return max([0.82 if interest in rule.aliases and tags & rule.tags else 0.0 for rule in RULES] or [0.0])


def _matching_rules(interest: str) -> tuple[InterestRule, ...]:
    return tuple(rule for rule in RULES if interest in rule.aliases)


def _categories(place: object) -> frozenset[str]:
    raw = str(getattr(place, "category", "") or "")
    return frozenset(_norm(item) for item in raw.split(",") if _norm(item))


def _tags(place: object) -> frozenset[str]:
    direct = getattr(place, "tags", None)
    if isinstance(direct, (list, tuple, set)):
        return frozenset(_norm(str(item)) for item in direct if _norm(str(item)))
    return frozenset()


def _fuzzy(interest: str, category: str) -> bool:
    return len(interest) >= 3 and (interest in category or category in interest)


def _norm(value: str) -> str:
    return value.strip().casefold().replace("_", "-")
