import re

from telegram_bot.services.text_intent.patterns import (
    AVOID_MARKERS,
    CATEGORY_KEYWORDS,
    ROUTE_MARKERS,
)


def contains_route_marker(text: str) -> bool:
    return _contains_any(text, ROUTE_MARKERS)


def mentioned_categories(text: str) -> tuple[str, ...]:
    return tuple(
        map(
            lambda item: item[0],
            filter(lambda item: _contains_any(text, item[1]), CATEGORY_KEYWORDS),
        )
    )


def avoided_categories(text: str) -> tuple[str, ...]:
    return tuple(
        map(
            lambda item: item[0],
            filter(lambda item: _is_avoided_category(text, item[1]), CATEGORY_KEYWORDS),
        )
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _is_avoided_category(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_avoid_pattern(keyword).search(text) for keyword in keywords)


def _avoid_pattern(keyword: str) -> re.Pattern[str]:
    markers = "|".join(map(re.escape, AVOID_MARKERS))
    return re.compile(rf"(?:{markers})[^.!?,\n]{{0,32}}{re.escape(keyword)}")
