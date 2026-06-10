from collections.abc import Callable
from functools import reduce

from models.place import Place
from services.place_address_policy import is_real_address
from services.place_staleness_policy import (
    PLACE_STATUS_ACTIVE,
    PLACE_STATUS_CLOSED,
    PLACE_STATUS_NEEDS_VERIFICATION,
    PLACE_STATUS_TEMPORARILY_CLOSED,
    effective_place_status,
)


def status_counts(places: list[Place]) -> dict[str, int]:
    empty = {
        PLACE_STATUS_ACTIVE: 0,
        PLACE_STATUS_NEEDS_VERIFICATION: 0,
        PLACE_STATUS_TEMPORARILY_CLOSED: 0,
        PLACE_STATUS_CLOSED: 0,
    }
    return reduce(_count_status, places, empty)


def average_confidence(places: list[Place]) -> float | None:
    values = list(filter(lambda value: value is not None, map(_confidence, places)))
    return None if not values else round(sum(values) / len(values), 3)


def _count_status(counts: dict[str, int], place: Place) -> dict[str, int]:
    status = effective_place_status(place)
    return {**counts, status: counts.get(status, 0) + 1}


def count(places: list[Place], predicate: Callable[[Place], bool]) -> int:
    return sum(1 for p in places if predicate(p))


def has_coordinates(place: Place) -> bool:
    return place.lat is not None and place.lng is not None


def has_opening_hours(place: Place) -> bool:
    return bool(place.opening_hours)


def has_visit_duration(place: Place) -> bool:
    return bool(place.average_visit_duration_minutes)


def has_source(place: Place) -> bool:
    return bool(getattr(place, "source", None))


def _confidence(place: Place) -> float | None:
    value = getattr(place, "confidence", None)
    return float(value) if isinstance(value, (int, float)) else None


def has_real_address(place: Place) -> bool:
    return is_real_address(getattr(place, "address", None))


def has_photo(place: Place) -> bool:
    return bool(getattr(place, "image_url", None))


def is_verified(place: Place) -> bool:
    return getattr(place, "verification_status", "unverified") == "verified"


def is_route_eligible(place: Place) -> bool:
    return bool(getattr(place, "is_route_eligible", False))


def publication_status_counts(places: list[Place]) -> dict[str, int]:
    result: dict[str, int] = {}
    for place in places:
        status = str(getattr(place, "publication_status", "unknown") or "unknown")
        result[status] = result.get(status, 0) + 1
    return result
