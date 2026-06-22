from __future__ import annotations

from datetime import datetime
from typing import Callable

from schemas.merged_context import MergedContext
from services.place_staleness_policy import is_route_usable_place


OpenState = Callable[[object, datetime], str]


def hard_reason(place: object, ctx: MergedContext, now: datetime, open_state: OpenState) -> str | None:
    checks = (
        _explicit_place_reason(place, ctx),
        _status_reason(place),
        _coordinate_reason(place),
        _category_reason(place, ctx),
        _hours_reason(place, ctx, now, open_state),
    )
    return next(filter(None, checks), None)


def budget_reason(place: object, ctx: MergedContext) -> str | None:
    price = getattr(place, "price_level", None)
    try:
        over_budget = price is not None and int(price) > int(ctx.budget_level)
    except (TypeError, ValueError):
        return None
    return "price_budget" if over_budget else None


def place_id(place: object) -> str:
    return str(getattr(place, "id", ""))


def _explicit_place_reason(place: object, ctx: MergedContext) -> str | None:
    ids = {str(item) for item in ctx.avoided_place_ids}
    return "explicit_place_exclude" if place_id(place) in ids else None


def _status_reason(place: object) -> str | None:
    return None if is_route_usable_place(place) else "status"


def _coordinate_reason(place: object) -> str | None:
    return "no_coordinates" if _has_bad_coordinates(place) else None


def _category_reason(place: object, ctx: MergedContext) -> str | None:
    categories = {_norm(item) for item in ctx.avoided_categories}
    return "avoided_category" if _category(place) in categories else None


def _hours_reason(place: object, ctx: MergedContext, now: datetime, open_state: OpenState) -> str | None:
    if not _is_now_mode(ctx):
        return None
    status = open_state(place, now)
    return _known_hours_reason(status) or _unknown_hours_reason(status, ctx)


def _known_hours_reason(status: str) -> str | None:
    return "closed_now" if status == "closed" else None


def _unknown_hours_reason(status: str, ctx: MergedContext) -> str | None:
    return "unknown_hours_time_sensitive" if status == "unknown" and _is_strict_hours_category(ctx) else None


def _is_now_mode(ctx: MergedContext) -> bool:
    mode = str(getattr(ctx, "route_time_mode", "") or "").casefold()
    time_of_day = str(getattr(ctx, "time_of_day", "") or "").casefold()
    return mode == "now" or time_of_day == "now"


def _is_strict_hours_category(ctx: MergedContext) -> bool:
    return bool(getattr(ctx, "require_known_hours", False))


def _has_bad_coordinates(place: object) -> bool:
    lat = getattr(place, "lat", None)
    lng = getattr(place, "lng", None)
    if not _is_number(lat) or not _is_number(lng):
        return True
    if float(lat) == 0.0 and float(lng) == 0.0:
        return True
    return not (-90.0 <= float(lat) <= 90.0 and -180.0 <= float(lng) <= 180.0)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _category(place: object) -> str:
    return _norm(str(getattr(place, "category", "") or ""))


def _norm(value: str) -> str:
    text = value.strip().casefold()
    return text[:-1] if len(text) > 3 and text.endswith("s") else text
