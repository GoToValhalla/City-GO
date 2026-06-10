from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextNearbyIntent:
    city_query: str


def parse_text_nearby_intent(text: str) -> TextNearbyIntent | None:
    normalized = _normalize(text)
    return (
        TextNearbyIntent(city_query=text)
        if normalized and _contains_nearby_marker(normalized)
        else None
    )


def _contains_nearby_marker(text: str) -> bool:
    return any(marker in text for marker in _NEARBY_MARKERS)


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


_NEARBY_MARKERS = (
    "что рядом",
    "места рядом",
    "рядом со мной",
    "поблизости",
    "недалеко",
)
