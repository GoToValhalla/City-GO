from __future__ import annotations

from html import escape


def warning_texts(route: dict[str, object]) -> list[str]:
    structured = route.get("user_warnings")
    if isinstance(structured, list):
        return [
            str(item.get("user_message"))
            for item in structured
            if isinstance(item, dict) and item.get("user_message")
        ]
    return _string_list(route.get("warnings"))


def warning_lines(warnings: list[str]) -> list[str]:
    if not warnings:
        return []
    return ["", "<b>Нюансы</b>", *[f"• {escape(warning)}" for warning in warnings[:3]]]


def _string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]
