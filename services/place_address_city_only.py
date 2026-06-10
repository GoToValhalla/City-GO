"""Определение city-only адреса без улицы (для assess/apply)."""

from __future__ import annotations

import re

from services.place_address_policy import normalized_address

_COUNTRY_TOKENS = frozenset({"россия", "russia", "грузия", "georgia", "армения", "armenia"})
_STREET_HINT = re.compile(
    r"(ул\.|улица|проспект|пр\.|пер\.|переулок|наб\.|набережная|шоссе|бульвар|тракт|"
    r"б-р|пл\.|площадь|lane|road|street|\d)",
    re.IGNORECASE,
)


def city_only_tokens(city_name: str | None, city_slug: str | None) -> frozenset[str]:
    tokens: set[str] = set()
    for raw in (city_name, city_slug):
        value = normalized_address(raw).casefold()
        if value:
            tokens.add(value)
            tokens.update(part.strip() for part in value.replace("-", " ").split() if len(part.strip()) > 3)
    return frozenset(tokens)


def is_city_only(address: str, *, city_name: str | None = None, city_slug: str | None = None) -> bool:
    lowered = normalized_address(address).casefold()
    if not lowered or lowered in _COUNTRY_TOKENS:
        return True
    tokens = city_only_tokens(city_name, city_slug)
    if lowered in tokens:
        return True
    parts = [part.strip() for part in address.split(",") if part.strip()]
    if len(parts) != 1:
        return False
    if tokens and any(token in lowered for token in tokens):
        return True
    return not _STREET_HINT.search(address)
