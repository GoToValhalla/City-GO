from __future__ import annotations

from urllib.parse import urlencode

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from core.config import settings
from models.bot_session import BotSession
from telegram_bot.callbacks import cb
from telegram_bot.quality import clean_title
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, Page
from telegram_bot.session import get_short_id
from telegram_bot.utils import compact_text

CITY_LIST_VISIBLE_LIMIT = 5
BUTTON_TITLE_LIMIT = 42


def main_menu() -> InlineKeyboardMarkup:
    rows = []
    mini_app_button = _mini_app_button("🚀 Открыть City GO", "/")
    if mini_app_button is not None:
        rows.append([mini_app_button])
    rows.extend(
        [
            [
                InlineKeyboardButton(text="🚶 Маршруты", callback_data=cb("r", "list", 0)),
                InlineKeyboardButton(text="📍 Рядом", callback_data=cb("near", "ask")),
            ],
            [
                InlineKeyboardButton(text="👀 Смотреть места", callback_data=cb("p", "cat", "sights", 0)),
                InlineKeyboardButton(text="☕ Еда и кофе", callback_data=cb("p", "cat", "food", 0)),
            ],
            [
                InlineKeyboardButton(text="🟢 Открыто", callback_data=cb("open", "list", 0)),
                InlineKeyboardButton(text="❤️ Сохранённое", callback_data=cb("fav", "list")),
            ],
            [
                InlineKeyboardButton(text="🏙 Город", callback_data=cb("c", "list")),
                InlineKeyboardButton(text="❓ Помощь", callback_data=cb("help")),
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
        rows.append([InlineKeyboardButton(text=_button_title(route.title), callback_data=cb("r", "view", get_short_id(session, route.id)))])
    rows += _pagination("r", "list", page.page, page.has_next)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_card(route: BotRoute, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, route.id)
    favorite_text, favorite_callback = _favorite_button("r", route.id, sid, session)
    rows = [
        [InlineKeyboardButton(text="🚶 Начать", callback_data=cb("r", "go", sid))],
        [InlineKeyboardButton(text="📋 Точки по порядку", callback_data=cb("r", "pts", sid))],
    ]
    mini_app_route = _mini_app_button("🗺 Открыть маршрут", f"/routes/{route.slug}") if route.slug else None
    if mini_app_route is not None:
        rows.append([mini_app_route])
    else:
        start_point = next((point for point in route.points if point.lat is not None and point.lng is not None), None)
        if start_point is not None:
            rows.append([_map_button("🗺 Открыть карту", start_point.lat, start_point.lng, start_point.title, start_point.address)])
    rows.extend(
        [
            [InlineKeyboardButton(text=favorite_text, callback_data=favorite_callback)],
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def generated_route_card(route: BotRoute) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🚶 Начать временную прогулку", callback_data=cb("r", "ggo"))],
        [InlineKeyboardButton(text="📋 Показать точки", callback_data=cb("r", "gpts"))],
    ]
    start_point = next((point for point in route.points if point.lat is not None and point.lng is not None), None)
    if start_point is not None:
        rows.append([_map_button("🗺 Первая точка на карте", start_point.lat, start_point.lng, start_point.title, start_point.address)])
    rows.extend(
        [
            [InlineKeyboardButton(text="👀 Смотреть места", callback_data=cb("p", "cat", "sights", 0))],
            [InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_step(point: BotRoutePoint, total: int, is_visited: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_visited:
        rows.append([InlineKeyboardButton(text="✅ Я на месте", callback_data=cb("rn", "visit", point.index))])
        rows.append([InlineKeyboardButton(text="↪️ Пропустить", callback_data=cb("rn", "skip", point.index))])
    nav = []
    if point.index > 0:
        nav.append(InlineKeyboardButton(text="← Предыдущая", callback_data=cb("rn", "pt", point.index - 1)))
    if point.index < total - 1:
        nav.append(InlineKeyboardButton(text="Следующая →", callback_data=cb("rn", "pt", point.index + 1)))
    if nav:
        rows.append(nav)
    if point.lat is not None and point.lng is not None:
        rows.append([_map_button("🗺 На карте", point.lat, point.lng, point.title, point.address)])
    rows.append([InlineKeyboardButton(text="🏁 Завершить", callback_data=cb("rn", "done"))])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def places_page(page: Page, session: BotSession, scope: str, action: str, *prefix_parts: object) -> InlineKeyboardMarkup:
    rows = []
    for place in page.items:
        assert isinstance(place, BotPlace)
        rows.append([InlineKeyboardButton(text=_button_title(place.title), callback_data=cb("p", "view", get_short_id(session, place.id)))])
    rows += _pagination(scope, action, page.page, page.has_next, *prefix_parts)
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def place_card(place: BotPlace, session: BotSession) -> InlineKeyboardMarkup:
    sid = get_short_id(session, place.id)
    favorite_text, favorite_callback = _favorite_button("p", place.id, sid, session)
    rows = []
    mini_app_place = _mini_app_button("ℹ️ Подробнее в City GO", f"/places/{place.slug}") if place.slug else None
    if mini_app_place is not None:
        rows.append([mini_app_place])
    if place.lat is not None and place.lng is not None:
        rows.append([_map_button("🗺 На карте", place.lat, place.lng, place.title, place.address)])
    rows.append([InlineKeyboardButton(text=favorite_text, callback_data=favorite_callback)])
    if place.category:
        rows.append([InlineKeyboardButton(text="🔍 Похожие", callback_data=cb("p", "cat", place.category, 0))])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorites_list(routes: list[BotRoute], places: list[BotPlace], session: BotSession) -> InlineKeyboardMarkup:
    rows = []
    for route in routes:
        rows.append([InlineKeyboardButton(text=f"🚶 {_button_title(route.title)}", callback_data=cb("r", "view", get_short_id(session, route.id)))])
    for place in places:
        rows.append([InlineKeyboardButton(text=f"📍 {_button_title(place.title)}", callback_data=cb("p", "view", get_short_id(session, place.id)))])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back"), InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))]])


def request_location() -> InlineKeyboardMarkup:
    rows = []
    mini_app_button = _mini_app_button("🚀 Открыть City GO", "/places")
    if mini_app_button is not None:
        rows.append([mini_app_button])
    rows.extend(
        [
            [InlineKeyboardButton(text="👀 Смотреть места", callback_data=cb("p", "cat", "sights", 0))],
            [InlineKeyboardButton(text="☕ Еда и кофе", callback_data=cb("p", "cat", "food", 0))],
            [InlineKeyboardButton(text="📍 Все места", callback_data=cb("p", "cat", "all", 0))],
            [InlineKeyboardButton(text="🏠 В меню", callback_data=cb("m", "main"))],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def _button_title(title: str) -> str:
    return compact_text(clean_title(title), BUTTON_TITLE_LIMIT) or "Место"


def _map_button(text: str, lat: float, lng: float, title: str | None = None, address: str | None = None) -> InlineKeyboardButton:
    mini_app_button = _mini_app_button(
        text,
        "/telegram/map",
        {
            "lat": lat,
            "lng": lng,
            "title": title or "Место",
            "address": address or "",
        },
    )
    if mini_app_button is not None:
        return mini_app_button
    return InlineKeyboardButton(text=text, url=_map_url(lat, lng))


def _mini_app_button(text: str, path: str, params: dict[str, object] | None = None) -> InlineKeyboardButton | None:
    url = _mini_app_url(path, params)
    if url is None:
        return None
    return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))


def _mini_app_url(path: str, params: dict[str, object] | None = None) -> str | None:
    base_url = settings.telegram_mini_app_url.strip().rstrip("/")
    if not base_url.startswith("https://"):
        return None
    normalized_path = path if path.startswith("/") else f"/{path}"
    query = urlencode({key: value for key, value in (params or {}).items() if value not in (None, "")})
    suffix = f"?{query}" if query else ""
    return f"{base_url}{normalized_path}{suffix}"


def _map_url(lat: float, lng: float) -> str:
    return f"https://yandex.ru/maps/?pt={lng},{lat}&z=16&l=map"