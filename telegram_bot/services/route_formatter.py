"""Top-level route message formatter for Telegram.

Компонует заголовок + сводку + качество + список точек.
Форматирование точки — в route_point_formatter.
"""

from __future__ import annotations

from html import escape

from telegram_bot.services.route_point_formatter import format_route_point
from telegram_bot.services.route_warning_formatter import warning_lines, warning_texts

_STATUS_TITLES = {
    "good": "<b>Маршрут готов</b>",
    "acceptable": "<b>Маршрут готов</b>",
    "weak": "<b>Маршрут собран с нюансами</b>",
    "failed": "<b>Маршрут не собрался</b>",
}

_STATUS_TEXTS = {
    "good": "Баланс точек, времени и данных выглядит нормально.",
    "acceptable": "Маршрут можно пройти, но есть небольшие компромиссы.",
    "weak": "Маршрут показываю, но лучше проверить нюансы ниже.",
    "failed": "Не удалось собрать готовый маршрут для этих параметров.",
}


def format_route_message(
    route: dict[str, object],
    place_titles: dict[str, str],
) -> str:
    points = _points(route)
    status = _quality_status(route)
    if not points:
        return _empty_route_message(route, status)

    lines = [
        _title(status),
        _summary_line(route),
        *_quality_lines(route, status),
        *warning_lines(warning_texts(route)),
        "",
        *[format_route_point(i, p, place_titles) for i, p in enumerate(points, 1)],
        "",
        "<b>Дальше</b>",
        "• отправь геолокацию, если хочешь стартовать от себя;",
        "• нажми «Открыть в картах» у точки;",
        "• напиши «маршрут на 4 часа», если нужно дольше.",
    ]
    return "\n".join(lines)


def _empty_route_message(route: dict[str, object], status: str | None = None) -> str:
    status = status or _quality_status(route)
    lines = [
        _title(status),
        escape(_STATUS_TEXTS.get(status, _STATUS_TEXTS["failed"])),
        "",
        "Что можно попробовать:",
        "• отправить геолокацию;",
        "• увеличить время маршрута;",
        "• сменить город;",
        "• открыть список мест.",
    ]
    return "\n".join([*lines, *warning_lines(warning_texts(route))])


def _summary_line(route: dict[str, object]) -> str:
    places = int(route.get("total_places") or 0)
    minutes = int(route.get("total_estimated_minutes") or route.get("total_minutes") or 0)
    meters = float(route.get("total_walk_distance_meters") or 0.0)
    distance = meters / 1000 if meters else float(route.get("estimated_distance") or 0.0)
    return f"{places} точек · {minutes} мин · {distance:.1f} км пешком"


def _points(route: dict[str, object]) -> list[dict[str, object]]:
    raw = route.get("points")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _quality_lines(route: dict[str, object], status: str) -> list[str]:
    quality = route.get("quality_score")
    status_text = _STATUS_TEXTS.get(status)
    lines: list[str] = []
    if status_text:
        lines.append(escape(status_text))
    if isinstance(quality, (int, float)):
        lines.append(f"Качество маршрута: <b>{round(float(quality) * 100)}%</b>")
    return lines


def _quality_status(route: dict[str, object]) -> str:
    direct = route.get("quality_status")
    if isinstance(direct, str) and direct:
        return direct
    breakdown = route.get("quality_breakdown")
    if isinstance(breakdown, dict):
        status = breakdown.get("status")
        if isinstance(status, str) and status:
            return status
    return "failed" if not _points(route) else "weak"


def _title(status: str) -> str:
    return _STATUS_TITLES.get(status, "<b>Маршрут готов</b>")
