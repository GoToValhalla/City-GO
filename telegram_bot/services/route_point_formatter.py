"""Formats a single route point for Telegram messages."""

from __future__ import annotations

from datetime import datetime
from html import escape

from telegram_bot.services.route_map_links import google_maps_link, point_location_text


def format_route_point(
    index: int,
    point: dict[str, object],
    titles: dict[str, str],
) -> str:
    """Строит компактную карточку точки маршрута для Telegram."""
    place_id = str(point.get("place_id") or "")
    title = escape(_title(point, place_id, titles))
    visit = int(point.get("visit_minutes") or 0)
    walk = int(point.get("estimated_walk_minutes") or point.get("walk_to_next_minutes") or 0)
    lat = float(point.get("lat") or 0)
    lng = float(point.get("lng") or 0)
    category = escape(str(point.get("category") or "место"))

    loc = point_location_text(point.get("address"), lat, lng)  # type: ignore[arg-type]
    map_link = google_maps_link(lat, lng)

    lines = [
        f"{index}. <b>{title}</b>",
        f"   {category} · {visit} мин",
        f"   📍 {escape(loc)}",
        f"   🧭 {map_link}",
        *_time_range_parts(point),
        *_walk_parts(walk),
        *_description_parts(point),
        *_warning_parts(point),
    ]
    return "\n".join(lines)


def _title(point: dict[str, object], place_id: str, titles: dict[str, str]) -> str:
    inline = point.get("title")
    if isinstance(inline, str) and inline.strip():
        return inline.strip()
    return titles.get(place_id) or f"Место #{place_id}"


def _time_range_parts(point: dict[str, object]) -> list[str]:
    arrival = _short_time(point.get("estimated_arrival_time"))
    departure = _short_time(point.get("estimated_departure_time"))
    if arrival and departure:
        return [f"   🕒 {arrival}-{departure}"]
    return [f"   🕒 с {arrival}"] if arrival else []


def _walk_parts(walk: int) -> list[str]:
    if walk <= 0:
        return []
    return [f"   🚶 {walk} мин до этой/следующей точки"]


def _description_parts(point: dict[str, object]) -> list[str]:
    raw = point.get("short_description")
    if not isinstance(raw, str) or not raw.strip():
        return []
    text = raw.strip()
    if len(text) > 140:
        text = f"{text[:137]}..."
    return [f"   {escape(text)}"]


def _warning_parts(point: dict[str, object]) -> list[str]:
    warning = point.get("time_warning")
    return [f"   Важно: {escape(str(warning))}"] if isinstance(warning, str) and warning else []


def _short_time(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw).strftime("%H:%M")
    except ValueError:
        return raw[:5] if len(raw) >= 5 else None
