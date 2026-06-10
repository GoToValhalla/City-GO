from html import escape

from telegram_bot.services.context_store import ContextSnapshot


def format_context_snapshot(snapshot: ContextSnapshot) -> str:
    return "\n".join(
        [
            "<b>Ваш контекст</b>",
            _status_line("Геолокация", snapshot["has_location"]),
            _address_line(snapshot["raw_address"]),
            _route_line(snapshot),
            "",
            "Можно продолжить маршрут или сбросить контекст.",
        ]
    )


def _status_line(label: str, enabled: bool) -> str:
    value = "есть" if enabled else "нет"
    return f"{label}: <b>{value}</b>"


def _address_line(raw_address: str | None) -> str:
    value = escape(raw_address) if raw_address else "нет"
    return f"Адрес: <b>{value}</b>"


def _route_line(snapshot: ContextSnapshot) -> str:
    if not snapshot["has_route"]:
        return "Маршрут: <b>нет</b>"
    return f"Маршрут: <b>есть, {snapshot['route_points']} точек</b>"
