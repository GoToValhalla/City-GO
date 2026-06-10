from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from telegram_bot.services.text_intent.matchers import avoided_categories

CorrectionAction = Literal[
    "remove_place",
    "shorten_route",
    "rebuild_from_here",
    "avoid_category",
    "extend_route",
]


@dataclass(frozen=True)
class TextCorrectionIntent:
    action: CorrectionAction
    avoided_categories: tuple[str, ...] = ()


_REMOVE_MARKERS = ("убери первую", "удали первую", "убрать первую")
_SHORTEN_MARKERS = ("короче", "сократи", "меньше точек", "покороче")
_EXTEND_MARKERS = ("добавь место", "длиннее", "ещё место", "еще место", "продли")
_REBUILD_MARKERS = ("перестрой отсюда", "заново отсюда", "отсюда")
_AVOID_MARKERS = ("без", "не хочу", "не надо", "избег")


def parse_text_correction_intent(text: str) -> TextCorrectionIntent | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    if _contains_any(normalized, _REBUILD_MARKERS):
        return TextCorrectionIntent(action="rebuild_from_here")
    if _contains_any(normalized, _REMOVE_MARKERS):
        return TextCorrectionIntent(action="remove_place")
    if _contains_any(normalized, _SHORTEN_MARKERS):
        return TextCorrectionIntent(action="shorten_route")
    if _contains_any(normalized, _EXTEND_MARKERS):
        return TextCorrectionIntent(action="extend_route")

    avoided = avoided_categories(normalized)
    if avoided:
        return TextCorrectionIntent(
            action="avoid_category",
            avoided_categories=avoided,
        )
    if _contains_any(normalized, _AVOID_MARKERS):
        return TextCorrectionIntent(action="avoid_category")
    return None


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)
