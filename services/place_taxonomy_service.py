"""
Сервис работы с каноничной таксономией City GO.
"""

from core.place_taxonomy import (
    PLACE_CATEGORIES,
    PLACE_RESTRICTION_TAGS,
    PLACE_SCENARIO_TAGS,
    PLACE_TAGS,
    PLACE_VIBE_TAGS,
)


def is_valid_place_category(value: str) -> bool:
    """
    Проверяет, что категория места входит в канон.
    """
    return value in PLACE_CATEGORIES


def is_valid_place_tag(value: str) -> bool:
    """
    Проверяет, что обычный тег места входит в канон.
    """
    return value in PLACE_TAGS


def is_valid_place_scenario_tag(value: str) -> bool:
    """
    Проверяет, что сценарный тег входит в канон.
    """
    return value in PLACE_SCENARIO_TAGS


def is_valid_place_vibe_tag(value: str) -> bool:
    """
    Проверяет, что vibe-тег входит в канон.
    """
    return value in PLACE_VIBE_TAGS


def is_valid_place_restriction_tag(value: str) -> bool:
    """
    Проверяет, что restriction-тег входит в канон.
    """
    return value in PLACE_RESTRICTION_TAGS


def validate_tag_list(values: list[str], validator) -> list[str]:
    """
    Возвращает только валидные значения из списка.

    Дубликаты убираются с сохранением порядка.
    """
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value in seen:
            continue
        if validator(value):
            result.append(value)
            seen.add(value)

    return result
