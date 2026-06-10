from functools import reduce
from typing import Any


def minimum_data_cap(route: list[Any]) -> float:
    missing = reduce(lambda acc, point: acc + _has_critical_gap(point), route, 0)
    return 0.6 if missing / max(1, len(route)) > 0.4 else 1.0


def _has_critical_gap(point: Any) -> int:
    has_hours = isinstance(getattr(point, "opening_hours", None), dict)
    has_price = isinstance(getattr(point, "price_level", None), int)
    return 0 if has_hours and has_price else 1
