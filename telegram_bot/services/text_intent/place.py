from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlaceIntentKind = Literal["open_now", "coffee", "food", "walks", "dog_friendly"]


@dataclass(frozen=True)
class TextPlaceIntent:
    kind: PlaceIntentKind
    search_query: str
    city_query: str | None = None


def parse_text_place_intent(text: str) -> TextPlaceIntent | None:
    raw_text = text.strip()
    normalized = _normalize(raw_text)

    if not normalized:
        return None

    kind = _intent_kind(normalized)
    if kind is None:
        return None

    return TextPlaceIntent(
        kind=kind,
        search_query=raw_text,
        city_query=_extract_city_query(
            raw_text=raw_text,
            normalized_text=normalized,
            kind=kind,
        ),
    )


def _intent_kind(text: str) -> PlaceIntentKind | None:
    match = next(
        iter(filter(lambda item: _contains_any(text, item[1]), _PATTERNS)),
        None,
    )
    return match[0] if match is not None else None


def _extract_city_query(
    raw_text: str,
    normalized_text: str,
    kind: PlaceIntentKind,
) -> str | None:
    """
    Извлекает город только если пользователь явно написал что-то кроме типа места.

    Примеры:
    - "Кофе" -> city_query=None
    - "Где кофе" -> city_query=None
    - "Кофе в Ереване" -> city_query="ереване"
    - "Ресторан в Кутаиси" -> city_query="кутаиси"

    Важно:
    search_query и city_query нельзя смешивать.
    "Кофе" — это запрос места, а не город.
    """
    candidate = normalized_text

    for needle in _PATTERNS_BY_KIND[kind]:
        candidate = candidate.replace(needle, " ")

    candidate = _normalize(candidate)
    candidate = _strip_city_query_noise(candidate)

    if not candidate:
        return None

    if candidate == normalized_text:
        return None

    if _contains_any(candidate, _NOISE_ONLY_WORDS):
        cleaned = _remove_noise_words(candidate)
        return cleaned or None

    return candidate


def _strip_city_query_noise(text: str) -> str:
    cleaned = _normalize(text)

    prefixes = (
        "в городе ",
        "во городе ",
        "в ",
        "во ",
        "у ",
        "около ",
        "возле ",
        "рядом с ",
        "рядом ",
    )

    changed = True
    while changed:
        changed = False

        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                changed = True

    return cleaned


def _remove_noise_words(text: str) -> str:
    words = [
        word
        for word in _normalize(text).split()
        if word not in _NOISE_ONLY_WORDS
    ]
    return " ".join(words).strip()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _normalize(text: str) -> str:
    return " ".join(word.strip(".,!?;:") for word in text.casefold().strip().split())


_PATTERNS: tuple[tuple[PlaceIntentKind, tuple[str, ...]], ...] = (
    ("open_now", ("что открыто", "открыто сейчас", "сейчас открыто")),
    ("coffee", ("где кофе", "кофе", "кофей", "капуч", "латте")),
    ("food", ("где поесть", "поесть", "еда", "ресторан", "обед", "ужин")),
    ("walks", ("куда погулять", "погуля", "прогул", "парк", "набереж")),
    ("dog_friendly", ("с собак", "с псом", "dog", "питомц")),
)

_PATTERNS_BY_KIND: dict[PlaceIntentKind, tuple[str, ...]] = {
    kind: patterns
    for kind, patterns in _PATTERNS
}

_NOISE_ONLY_WORDS = (
    "где",
    "найди",
    "найти",
    "покажи",
    "показать",
    "место",
    "места",
    "тип",
)
