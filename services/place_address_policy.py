"""Единая политика классификации адресов мест."""

from __future__ import annotations

import re

PLACEHOLDER_ADDRESSES: frozenset[str] = frozenset({
    "",
    "адрес уточняется",
    "адрес не указан",
    "нет адреса",
    "unknown",
    "-",
})

GENERIC_EXACT: frozenset[str] = frozenset({
    "центр города",
    "у моря",
    "променад",
    "центральный променад",
    "парк",
    "пляж",
    "набережная",
})

VENUE_CATEGORIES: frozenset[str] = frozenset({
    "cafe",
    "coffee",
    "food",
    "restaurant",
    "museum",
    "gallery",
    "culture",
})

LOCATION_CATEGORIES: frozenset[str] = frozenset({
    "walk",
    "park",
    "beach",
    "outdoor",
    "viewpoint",
})

_STREET_HINT = re.compile(
    r"(ул\.|улица|проспект|пр\.|пер\.|переулок|наб\.|набережная|шоссе|бульвар|тракт|"
    r"б-р|пл\.|площадь|lane|road|street|\d)",
    re.IGNORECASE,
)

MISSING_ADDRESS_DISPLAY = "Адрес уточняется · открыть на карте"


def normalized_address(address: str | None) -> str:
    return str(address or "").strip()


def is_placeholder_address(address: str | None) -> bool:
    value = normalized_address(address).casefold()
    if value in PLACEHOLDER_ADDRESSES:
        return True
    return value.startswith("координаты ") or "координаты" in value


def is_real_address(address: str | None) -> bool:
    value = normalized_address(address)
    return bool(value) and not is_placeholder_address(value)


def is_generic_address(address: str | None, category: str | None = None) -> bool:
    value = normalized_address(address)
    if not value or is_placeholder_address(value):
        return False
    lowered = value.casefold()
    if lowered in GENERIC_EXACT:
        return True
    cat = str(category or "").casefold()
    if cat not in VENUE_CATEGORIES:
        return False
    if _STREET_HINT.search(value):
        return False
    return len(value) < 28


def needs_backfill(address: str | None) -> bool:
    return is_placeholder_address(address) or not normalized_address(address)


def is_literal_placeholder_address(address: str | None) -> bool:
    value = normalized_address(address).casefold()
    return value in {"адрес не указан", "адрес уточняется", "нет адреса"}


def is_empty_address(address: str | None) -> bool:
    return not normalized_address(address)


def needs_recovery(address: str | None, category: str | None = None, *, include_generic: bool = False) -> bool:
    if needs_backfill(address):
        return True
    return include_generic and is_generic_address(address, category)


def is_replaceable_address(address: str | None, category: str | None = None) -> bool:
    if needs_backfill(address):
        return True
    return is_generic_address(address, category)


def should_apply_geocode_result(address: str | None, category: str | None) -> bool:
    if not is_real_address(address):
        return False
    cat = str(category or "").casefold()
    if is_generic_address(address, category) and cat in VENUE_CATEGORIES:
        return False
    return True


def is_unclear_for_display(address: str | None, category: str | None = None) -> bool:
    if not is_real_address(address):
        return True
    cat = str(category or "").casefold()
    return is_generic_address(address, category) and cat in VENUE_CATEGORIES
