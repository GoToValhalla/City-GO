from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.callbacks import build_callback
from bot.schemas import BotCity, BotPlace, BotRoute, PaginatedResult
from bot.session import get_short_id
from models.bot_session import BotSession


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚶 Маршруты", callback_data=build_callback("r", "list", 0)),
                InlineKeyboardButton(text="📍 Места рядом", callback_data=build_callback("near")),
            ],
            [
                InlineKeyboardButton(text="👀 Что посмотреть", callback_data=build_callback("p", "cat", "sights", 0)),
                InlineKeyboardButton(text="☕ Еда и кофе", callback_data=build_callback("p", "cat", "food", 0)),
            ],
            [
                InlineKeyboardButton(text="🕐 Открыто сейчас", callback_data=build_callback("open", 0)),
                InlineKeyboardButton(text="❤️ Избранное", callback_data=build_callback("fav")),
            ],
            [
                InlineKeyboardButton(text="🏙 Сменить город", callback_data=build_callback("c", "list")),
                InlineKeyboardButton(text="❓ Помощь", callback_data=build_callback("help")),
            ],
        ]
    )


def city_list(cities: list[BotCity]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=city.name, callback_data=build_callback("c", "set", city.slug))] for city in cities]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def routes_list(result: PaginatedResult, session: BotSession) -> InlineKeyboardMarkup:
    rows = []
    for route in result.items:
        assert isinstance(route, BotRoute)
        short_id = get_short_id(session, route.id)
        rows.append([InlineKeyboardButton(text=route.title, callback_data=build_callback("r", "view", short_id))])
    rows.extend(_pagination_rows("r:list", result.page, result.has_next))
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_card(route: BotRoute, session: BotSession) -> InlineKeyboardMarkup:
    short_id = get_short_id(session, route.id)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚶 Начать маршрут", callback_data=build_callback("r", "go", short_id))],
            [InlineKeyboardButton(text="📋 Все точки", callback_data=build_callback("r", "pts", short_id))],
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=build_callback("m", "main"))],
        ]
    )


def places_list(result: PaginatedResult, session: BotSession, callback_prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for place in result.items:
        assert isinstance(place, BotPlace)
        short_id = get_short_id(session, place.id)
        rows.append([InlineKeyboardButton(text=place.title, callback_data=build_callback("p", "view", short_id))])
    rows.extend(_pagination_rows(callback_prefix, result.page, result.has_next))
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def place_card() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=build_callback("m", "main"))],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data=build_callback("m", "main"))]])


def location_request() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Поделиться геолокацией", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _pagination_rows(prefix: str, page: int, has_next: bool) -> list[list[InlineKeyboardButton]]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="←", callback_data=f"{prefix}:{page - 1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="→", callback_data=f"{prefix}:{page + 1}"))
    return [row] if row else []
