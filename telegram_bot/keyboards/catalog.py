from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.bot_session import BotSession
from telegram_bot.callbacks import cb
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, Page
from telegram_bot.session import get_short_id

CITY_LIST_VISIBLE_LIMIT = 5


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


def city_list(cities: list[BotCity], *, limit: int = CITY_LIST_VISIBLE_LIMIT) -> InlineKeyboardMarkup:
    rows = []
    for city in cities[:limit]:
        suffix = f" · {city.places_count} мест" if city.places_count else ""
        rows.append([InlineKeyboardButton(text=f"{city.name}{suffix}", callback_data=cb("c", "set", city.slug))])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def routes_page(page: Page, session: BotSession) -> InlineKeyboardMarkup:
    rows = []
    for route in page.items:
        assert isinstance(route, BotRoute)
        rows.append([InlineKeyboardButton(text=route.title, callback_data=cb("r", "view", get_short_id(session, route.id)))])
    rows += _pagination("r", "list", page.page, page.has_next)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_card(route: BotRoute, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, route.id)
    favorite_text, favorite_callback = _favorite_button("r", route.id, sid, session)
    rows = [
        [InlineKeyboardButton(text="🚶 Начать маршрут", callback_data=cb("r", "go", sid))],
        [InlineKeyboardButton(text="📋 Все точки", callback_data=cb("r", "pts", sid))],
    ]
    start_point = next((point for point in route.points if point.lat is not None and point.lng is not None), None)
    if start_point is not None:
        rows.append([InlineKeyboardButton(text="🗺 Открыть карту", url=_map_url(start_point.lat, start_point.lng))])
    rows.extend(
        [
            [InlineKeyboardButton(text=favorite_text, callback_data=favorite_callback)],
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_step(point: BotRoutePoint, total: int, is_visited: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_visited:
        rows.append([InlineKeyboardButton(text="✅ Я на месте", callback_data=cb("rn", "visit", point.index))])
        rows.append([InlineKeyboardButton(text="⏭ Пропустить точку", callback_data=cb("rn", "skip", point.index))])
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
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def place_card(place: BotPlace, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, place.id)
    favorite_text, favorite_callback = _favorite_button("p", place.id, sid, session)
    rows = []
    if place.lat is not None and place.lng is not None:
        rows.append([InlineKeyboardButton(text="🗺 На карте", url=_map_url(place.lat, place.lng))])
    rows.append([InlineKeyboardButton(text=favorite_text, callback_data=favorite_callback)])
    if place.category:
        rows.append([InlineKeyboardButton(text="🔍 Похожие", callback_data=cb("p", "cat", place.category, 0))])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorites_list(routes: list[BotRoute], places: list[BotPlace], session: BotSession) -> InlineKeyboardMarkup:
    rows = []
    for route in routes:
        rows.append([InlineKeyboardButton(text=f"🚶 {route.title}", callback_data=cb("r", "view", get_short_id(session, route.id)))])
    for place in places:
        rows.append([InlineKeyboardButton(text=f"📍 {place.title}", callback_data=cb("p", "view", get_short_id(session, place.id)))])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))]])


def request_location() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👀 Что посмотреть", callback_data=cb("p", "cat", "sights", 0))],
            [InlineKeyboardButton(text="☕ Еда и кофе", callback_data=cb("p", "cat", "food", 0))],
            [InlineKeyboardButton(text="📍 Все места города", callback_data=cb("p", "cat", "all", 0))],
            [InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )


def _pagination(scope: str, action: str, page: int, has_next: bool, *prefix_parts: object) -> list[list[InlineKeyboardButton]]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="←", callback_data=cb(scope, action, *prefix_parts, page - 1)))
    if has_next:
        row.append(InlineKeyboardButton(text="→", callback_data=cb(scope, action, *prefix_parts, page + 1)))
    return [row] if row else []


def _favorite_button(kind: str, entity_id: int, short_id: str, session: BotSession) -> tuple[str, str]:
    key = "routes" if kind == "r" else "places"
    is_saved = entity_id in (session.favorites or {}).get(key, [])
    action = "del" if is_saved else "add"
    text = "💔 Убрать" if is_saved else "❤️ Сохранить"
    return text, cb("fav", action, kind, short_id)


def _map_url(lat: float, lng: float) -> str:
    return f"https://yandex.ru/maps/?pt={lng},{lat}&z=16&l=map"