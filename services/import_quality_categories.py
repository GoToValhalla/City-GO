"""
Константы и типы классификации для Import Quality Gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES

__all__ = [
    "PUBLIC_HIDDEN_CATEGORIES",
    "HIDDEN_CONFIDENCE_THRESHOLD",
    "AUTO_PUBLISH_CONFIDENCE_THRESHOLD",
    "ROUTE_ELIGIBLE_CATEGORIES",
    "NON_TOURIST_CATEGORIES",
    "DYNAMIC_CATEGORIES",
    "PublicationDecision",
    "auto_publish_decision",
    "needs_review_decision",
    "hidden_decision",
]

HIDDEN_CONFIDENCE_THRESHOLD: float = 0.2
AUTO_PUBLISH_CONFIDENCE_THRESHOLD: float = 0.5

ROUTE_ELIGIBLE_CATEGORIES: frozenset[str] = frozenset({
    "coffee", "food", "walk", "museum", "attraction",
    "beach", "park", "bar",
    "cafe", "culture", "viewpoint", "sight", "restaurant",
})

# Хранятся в БД, но НЕ в туристическом каталоге; future service/useful слой.
NON_TOURIST_CATEGORIES: frozenset[str] = frozenset({
    "health",   # аптеки, клиники, больницы
    "pharmacy",
    "service",  # сервисные точки, мастерские
    "services",
    "bus_stop",
    "stop",
    "public_transport",
    "transport",
})

DYNAMIC_CATEGORIES: frozenset[str] = frozenset({
    "bar", "cafe", "coffee", "food", "restaurant",
})


@dataclass(frozen=True)
class PublicationDecision:
    """Результат оценки качества импортируемого места."""

    decision: str  # "auto_publish" | "needs_review" | "hidden"
    reason: str
    is_published: bool
    is_visible_in_catalog: bool
    is_route_eligible: bool
    is_searchable: bool
    publication_status: str


def auto_publish_decision(category: str | None) -> PublicationDecision:
    route_elig = bool(category and category in ROUTE_ELIGIBLE_CATEGORIES)
    return PublicationDecision(
        decision="auto_publish", reason="quality_ok",
        is_published=True, is_visible_in_catalog=True,
        is_route_eligible=route_elig, is_searchable=True,
        publication_status="published",
    )


def needs_review_decision(reason: str) -> PublicationDecision:
    return PublicationDecision(
        decision="needs_review", reason=reason,
        is_published=False, is_visible_in_catalog=False,
        is_route_eligible=False, is_searchable=False,
        publication_status="needs_review",
    )


def hidden_decision(reason: str) -> PublicationDecision:
    return PublicationDecision(
        decision="hidden", reason=reason,
        is_published=False, is_visible_in_catalog=False,
        is_route_eligible=False, is_searchable=False,
        publication_status="hidden",
    )
