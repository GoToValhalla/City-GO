from __future__ import annotations

import math


def clamp_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def format_duration(minutes: int | None) -> str | None:
    if minutes is None or minutes <= 0:
        return None
    if minutes < 60:
        return f"~{minutes} мин"
    hours, rest = divmod(minutes, 60)
    if rest == 0:
        return f"~{hours} ч"
    return f"~{hours} ч {rest} мин"


def format_distance_km(distance_km: float | None) -> str | None:
    if distance_km is None or distance_km <= 0:
        return None
    if distance_km < 1:
        return f"{round(distance_km * 1000)} м"
    return f"{distance_km:.1f} км"


def format_distance_m(distance_m: int | float | None) -> str | None:
    if distance_m is None:
        return None
    if distance_m < 1000:
        return f"{int(round(distance_m))} м"
    return f"{distance_m / 1000:.1f} км"


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return int(round(radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))))
