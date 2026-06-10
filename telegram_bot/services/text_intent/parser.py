from __future__ import annotations

import re
from dataclasses import dataclass

from telegram_bot.services.text_intent.matchers import (
    avoided_categories,
    contains_route_marker,
    mentioned_categories,
)
from telegram_bot.services.text_intent.patterns import (
    DEFAULT_MINUTES,
    WORD_MINUTES,
)


@dataclass(frozen=True)
class TextRouteIntent:
    minutes: int
    interests: tuple[str, ...]
    avoided_categories: tuple[str, ...]
    city_query: str | None = None


def parse_text_route_intent(text: str) -> TextRouteIntent | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    avoided = avoided_categories(normalized)
    interests = tuple(
        filter(
            lambda category: category not in avoided,
            mentioned_categories(normalized),
        )
    )
    minutes = _extract_minutes(normalized)

    if not _is_route_request(normalized, minutes, interests, avoided):
        return None

    return TextRouteIntent(
        minutes=minutes or DEFAULT_MINUTES,
        interests=interests,
        avoided_categories=avoided,
        city_query=text,
    )


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


def _extract_minutes(text: str) -> int | None:
    minute_match = re.search(r"\b(\d{1,4})\s*(?:мин|минут)", text)
    hour_match = re.search(r"\b(\d{1,2})\s*(?:ч|час|часа|часов)", text)

    if minute_match:
        return _clamp_minutes(int(minute_match.group(1)))
    if hour_match:
        return _clamp_minutes(int(hour_match.group(1)) * 60)
    return _word_minutes(text)


def _word_minutes(text: str) -> int | None:
    values = tuple(
        map(
            lambda item: item[1],
            filter(lambda item: item[0] in text, WORD_MINUTES),
        )
    )
    return next(iter(values), None)


def _clamp_minutes(value: int) -> int:
    return max(15, min(value, 1440))


def _is_route_request(
    text: str,
    minutes: int | None,
    interests: tuple[str, ...],
    avoided: tuple[str, ...],
) -> bool:
    has_route_marker = contains_route_marker(text)
    has_route_shape = minutes is not None and bool(interests or avoided)
    return has_route_marker or has_route_shape
