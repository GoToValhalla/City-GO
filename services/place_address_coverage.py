"""Агрегация покрытия адресов по городам."""

from __future__ import annotations

from typing import Any

from models.place import Place
from services.place_address_policy import (
    is_empty_address,
    is_generic_address,
    is_literal_placeholder_address,
    is_placeholder_address,
    is_real_address,
    is_unclear_for_display,
)


def city_address_report(places: list[Place]) -> dict[str, Any]:
    buckets = _empty_buckets()
    for place in places:
        _accumulate(buckets, place)
    return dict(buckets)


def _empty_buckets() -> dict[str, Any]:
    return {
        "total_places": 0,
        "published_places": 0,
        "visible_in_catalog": 0,
        "route_eligible": 0,
        "with_real_address": 0,
        "without_address": 0,
        "address_not_specified_count": 0,
        "literal_placeholder_count": 0,
        "empty_address_count": 0,
        "address_unclear_count": 0,
        "generic_address_count": 0,
        "samples_missing": [],
        "samples_generic": [],
        "route_eligible_without_address": 0,
        "published_without_address": 0,
    }


def _accumulate(buckets: dict[str, Any], place: Place) -> None:
    buckets["total_places"] += 1
    address = place.address
    category = str(getattr(place, "category", "") or "")
    real = is_real_address(address)
    generic = is_generic_address(address, category)
    unclear = is_unclear_for_display(address, category)
    if getattr(place, "is_published", False):
        buckets["published_places"] += 1
    if getattr(place, "is_visible_in_catalog", False):
        buckets["visible_in_catalog"] += 1
    if getattr(place, "is_route_eligible", False):
        buckets["route_eligible"] += 1
    if real and not generic:
        buckets["with_real_address"] += 1
    if not real:
        buckets["without_address"] += 1
        _append_sample(buckets["samples_missing"], place, address)
    if is_placeholder_address(address):
        buckets["address_not_specified_count"] += 1
    if is_literal_placeholder_address(address):
        buckets["literal_placeholder_count"] += 1
    if is_empty_address(address):
        buckets["empty_address_count"] += 1
    if unclear:
        buckets["address_unclear_count"] += 1
    if generic:
        buckets["generic_address_count"] += 1
        _append_sample(buckets["samples_generic"], place, address)
    if getattr(place, "is_route_eligible", False) and unclear:
        buckets["route_eligible_without_address"] += 1
    if str(getattr(place, "publication_status", "")) == "published" and unclear:
        buckets["published_without_address"] += 1


def _append_sample(samples: list[dict[str, object]], place: Place, address: str | None) -> None:
    if len(samples) >= 5:
        return
    samples.append({"id": place.id, "title": place.title, "address": address, "category": place.category})
