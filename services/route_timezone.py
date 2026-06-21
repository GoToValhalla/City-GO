from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_ROUTE_TIMEZONE = "UTC"


def timezone_name(ctx: object) -> str:
    value = str(getattr(ctx, "timezone", "") or "").strip()
    return value or DEFAULT_ROUTE_TIMEZONE


def zoneinfo_for_ctx(ctx: object) -> ZoneInfo:
    name = timezone_name(ctx)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_ROUTE_TIMEZONE)


def local_now(ctx: object) -> datetime:
    return datetime.now(zoneinfo_for_ctx(ctx))


def ensure_local_datetime(value: datetime, ctx: object) -> datetime:
    zone = zoneinfo_for_ctx(ctx)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).astimezone(zone)
    return value.astimezone(zone)
