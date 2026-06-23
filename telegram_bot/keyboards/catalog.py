from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from models.bot_session import BotSession
from telegram_bot.callbacks import cb
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, Page
from telegram_bot.session import get_short_id


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚶 Маршруты", callback_data=cb("r", "list", 0)),
                InlineKeyboardButton(text="📍 Места рядом", callback_data=cb("near", "ask")),
            ],
            [
                InlineKeyboardButton(text="👀 Что посмотреть", callback_data=cb("p", "cat", "sights", 0)),
                InlineKeyboardButton(text="☕ Еда и кофе", callback_data=cb("p", "cat", "food", 0)),
            ],
            [
                InlineKeyboardButton(text="🕐 Открыто сейчас", callback_data=cb("open", "list", 0)),
                InlineKeyboardButton(text="❤️ Избранное", callback_data=cb("fav", "list")),
            ],
            [
                InlineKeyboardButton(text="🏙 Сменить город", callback_data=cb("c", "list")),
                InlineKeyboardButton(text="❓ Помощь", callback_data=cb("help")),
            ],
        ]
    )


def city_list(cities: list[BotCity]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=city.name, callback_data=cb("c", "set", city.slug))] for city in cities]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def routes_page(page: Page, session: BotSession) -> InlineKeyboardMarkup:
    rows = []
    for route in page.items:
        assert isinstance(route, BotRoute)
        rows.append([InlineKeyboardButton(text=route.title, callback_data=cb("r", "view", get_short_id(session, route.id)))])
    rows += _pagination("r", "list", page.page, page.has_next)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_card(route: BotRoute, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, route.id)
    favorite_text = "💔 Убрать" if route.id in (session.favorites or {}).get("routes", []) else "❤️ Сохранить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚶 Начать маршрут", callback_data=cb("r", "go", sid))],
            [InlineKeyboardButton(text="📋 Все точки", callback_data=cb("r", "pts", sid))],
            [InlineKeyboardButton(text=favorite_text, callback_data=cb("fav", "toggle", "r", sid))],
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )


def route_step(point: BotRoutePoint, total: int, is_visited: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_visited:
        rows.append([InlineKeyboardButton(text="✅ Я на месте", callback_data=cb("rn", "visit", point.index))])
    nav = []
    if point.index > 0:
        nav.append(InlineKeyboardButton(text="← Предыдущая", callback_data=cb("rn", "pt", point.index - 1)))
    if point.index < total - 1:
        nav.append(InlineKeyboardButton(text="Следующая →", callback_data=cb("rn", "pt", point.index + 1)))
    if nav:
        rows.append(nav)
    if point.lat is not None and point.lng is not None:
        rows.append([InlineKeyboardButton(text="🗺 На карте", url=_map_url(point.lat, point.lng))])
    rows.append([InlineKeyboardButton(text="🏁 Завершить", callback_data=cb("rn", "done"))])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def places_page(page: Page, session: BotSession, scope: str, action: str, *prefix_parts: object) -> InlineKeyboardMarkup:
    rows = []
    for place in page.items:
        assert isinstance(place, BotPlace)
        rows.append([InlineKeyboardButton(text=place.title, callback_data=cb("p", "view", get_short_id(session, place.id)))])
    rows += _pagination(scope, action, page.page, page.has_next, *prefix_parts)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def place_card(place: BotPlace, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, place.id)
    favorite_text = "💔 Убрать" if place.id in (session.favorites or {}).get("places", []) else "❤️ Сохранить"
    rows = []
    if place.lat is not None and place.lng is not None:
        rows.append([InlineKeyboardButton(text="🗺 На карте", url=_map_url(place.lat, place.lng))])
    rows.append([InlineKeyboardButton(text=favorite_text, callback_data=cb("fav", "toggle", "p", sid))])
    if place.category:
        rows.append([InlineKeyboardButton(text="🔍 Похожие", callback_data=cb("p", "cat", place.category, 0))])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))]])


def request_location() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Поделиться геолокацией", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _pagination(scope: str, action: str, page: int, has_next: bool, *prefix_parts: object) -> list[list[InlineKeyboardButton]]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="←", callback_data=cb(scope, action, *prefix_parts, page - 1)))
    if has_next:
        row.append(InlineKeyboardButton(text="→", callback_data=cb(scope, action, *prefix_parts, page + 1)))
    return [row] if row else []


def _map_url(lat: float, lng: float) -> str:
    return f"https://yandex.ru/maps/?pt={lng},{lat}&z=16&l=map"
