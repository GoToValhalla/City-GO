from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardRemove

from telegram_bot.keyboards.main_menu import get_location_request_keyboard, get_main_menu_keyboard
from telegram_bot.keyboards.route_actions import get_route_actions_keyboard
from telegram_bot.services.route_formatter import format_route_message


def _button_texts(markup) -> list[str]:
    rows = getattr(markup, "keyboard", None) or getattr(markup, "inline_keyboard", None) or []
    return [button.text for row in rows for button in row]


def test_main_keyboard_removes_persistent_reply_keyboard_new() -> None:
    keyboard = get_main_menu_keyboard()
    assert isinstance(keyboard, ReplyKeyboardRemove)
    assert keyboard.remove_keyboard is True


def test_location_keyboard_exposes_location_request_new() -> None:
    keyboard = get_location_request_keyboard()
    texts = _button_texts(keyboard)
    assert "Отправить геопозицию" in texts
    location_buttons = [button for row in keyboard.keyboard for button in row if button.text == "Отправить геопозицию"]
    assert location_buttons
    assert location_buttons[0].request_location is True


def test_route_actions_keyboard_exposes_extend_route_new() -> None:
    keyboard = get_route_actions_keyboard()
    assert isinstance(keyboard, InlineKeyboardMarkup)
    texts = _button_texts(keyboard)
    assert "Добавить точку" in texts
    assert "Маршрут короче" in texts
    assert "Перестроить отсюда" in texts


def test_route_formatter_handles_weak_status_new() -> None:
    route = {
        "route_id": "r1",
        "quality_status": "weak",
        "quality_score": 0.44,
        "total_places": 1,
        "total_estimated_minutes": 30,
        "total_walk_distance_meters": 800,
        "warnings": ["some_places_have_no_photo"],
        "points": [
            {
                "place_id": "1",
                "title": "Test place",
                "category": "museum",
                "visit_minutes": 20,
                "estimated_walk_minutes": 10,
                "lat": 55.0,
                "lng": 20.0,
                "address": "Test address",
                "short_description": "Short text",
            }
        ],
    }
    text = format_route_message(route, {})
    assert "Маршрут собран с нюансами" in text
    assert "Качество маршрута" in text
    assert "Test place" in text


def test_route_formatter_handles_failed_empty_route_new() -> None:
    route = {
        "route_id": "r2",
        "quality_status": "failed",
        "quality_score": 0.0,
        "warnings": ["route_failed_no_places"],
        "points": [],
    }
    text = format_route_message(route, {})
    assert "Маршрут не собрался" in text
    assert "Что можно попробовать" in text
