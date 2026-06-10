"""
Import Publication Gate.

assess_import_quality() — чистая функция, без обращений к БД.
Определяет статус публикации нового импортируемого места.
"""

from __future__ import annotations

from services.import_quality_categories import (
    AUTO_PUBLISH_CONFIDENCE_THRESHOLD,
    DYNAMIC_CATEGORIES,
    HIDDEN_CONFIDENCE_THRESHOLD,
    NON_TOURIST_CATEGORIES,
    PUBLIC_HIDDEN_CATEGORIES,
    PublicationDecision,
    auto_publish_decision,
    hidden_decision,
    needs_review_decision,
)


def assess_import_quality(
    *,
    title: str | None,
    lat: float | None,
    lng: float | None,
    category: str | None,
    confidence: float | None,
    source: str | None,
    address: str | None = None,
    opening_hours: dict[str, object] | None = None,
) -> PublicationDecision:
    """
    Порядок: жёсткие rejection → нетуристические → мягкие review → auto_publish.
    """
    # Hard rejections → hidden
    if not (title and title.strip()):
        return hidden_decision("no_title")
    if not _has_valid_coords(lat, lng):
        return hidden_decision("no_coordinates")
    if category and category in PUBLIC_HIDDEN_CATEGORIES:
        return hidden_decision("hidden_category")
    if confidence is not None and confidence < HIDDEN_CONFIDENCE_THRESHOLD:
        return hidden_decision("low_confidence")

    # Нетуристические → needs_review (хранятся, но не в tourist catalog)
    if category and category in NON_TOURIST_CATEGORIES:
        return needs_review_decision("non_tourist_category")

    # Soft review signals
    if confidence is not None and confidence < AUTO_PUBLISH_CONFIDENCE_THRESHOLD:
        return needs_review_decision("low_confidence")
    if source is None:
        return needs_review_decision("no_source")
    if _is_dynamic(category) and not address and opening_hours is None:
        return needs_review_decision("missing_hours_for_dynamic_category")

    return auto_publish_decision(category)


def _has_valid_coords(lat: float | None, lng: float | None) -> bool:
    return lat is not None and lng is not None and not (lat == 0.0 and lng == 0.0)


def _is_dynamic(category: str | None) -> bool:
    return bool(category and category in DYNAMIC_CATEGORIES)
