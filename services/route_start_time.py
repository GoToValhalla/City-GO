from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

BUCKETS = {
    "morning": time(9, 0),
    "afternoon": time(14, 0),
    "evening": time(19, 0),
    "night": time(22, 30),
}


def effective_route_start(now: datetime, time_of_day: object) -> datetime:
    now = _assume_utc_if_naive(now)
    target = BUCKETS.get(str(time_of_day or "").strip().casefold())
    if target is None:
        return now
    planned = now.replace(hour=target.hour, minute=target.minute, second=0, microsecond=0)
    return planned + timedelta(days=1) if planned <= now else planned


def _assume_utc_if_naive(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
