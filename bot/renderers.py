from __future__ import annotations

from html import escape

from bot.quality import clean_title
from bot.schemas import BotCity, BotPlace, BotRoute
from bot.utils import clamp_text, format_distance_km, format_distance_m, format_duration

CATEGORY_LABELS = {
    "culture": ("🏛", "Культура"),
    "museum": ("🏛", "Музей"),
    "park": ("🌿", "Парк"),
    "walk": ("🚶", "Прогулка"),
    "viewpoint": ("👀", "Смотровая точка"),
    "food": ("🍽", "Еда"),
    "coffee": ("☕", "Кофе"),
    "cafe": ("☕", "Кофе"),
    "hotel": ("🏨", "Проживание"),
    "beach": ("🌊", "Пляж"),
    "useful": ("ℹ️", "Полезное"),
}


def render_start() -> str:
    return (
        "<b>Привет! Я City GO.</b>\n\n"
        "Помогу найти маршруты, интересные места, кафе и точки рядом.\n"
        "Выбери город, и начнем."
    )


def render_city_select(cities: list[BotCity]) -> str:
    if not cities:
        return "<b>Пока нет опубликованных городов.</b>\n\nВернись позже: каталог еще готовится."
    return "<b>С какого города начнем?</b>"


def render_main_menu(city: BotCity) -> str:
    return f"<b>🏙 {escape(city.name)}</b>\n\nЧто хочешь найти?"


def render_routes_list(city: BotCity, routes: list[BotRoute], page: int) -> str:
    if not routes:
        return (
            f"<b>Маршруты для города {escape(city.name)} появятся скоро.</b>\n\n"
            "Пока можно посмотреть места и кафе."
        )
    lines = [f"<b>🚶 Маршруты: {escape(city.name)}</b>", ""]
    for index, route in enumerate(routes, start=page * 5 + 1):
        meta = _route_meta(route)
        suffix = f" · {escape(meta)}" if meta else ""
        lines.append(f"{index}. {escape(route.title)}{suffix}")
    return "\n".join(lines)


def render_route_card(route: BotRoute) -> str:
    lines = [f"<b>🚶 {escape(route.title)}</b>", ""]
    description = clamp_text(route.short_description, 220)
    if description:
        lines.extend([escape(description), ""])
    meta = _route_meta(route)
    if meta:
        lines.extend([escape(meta), ""])
    if route.points:
        lines.append("<b>Точки маршрута:</b>")
        for point in route.points[:5]:
            lines.append(f"{point.index + 1}. {escape(clean_title(point.title))}")
        if len(route.points) > 5:
            lines.append(f"…еще {len(route.points) - 5}")
    return "\n".join(lines).strip()


def render_places_list(title: str, places: list[BotPlace], page: int) -> str:
    if not places:
        return (
            f"<b>{escape(title)}</b>\n\n"
            "Ничего не нашлось. Попробуй другую категорию или вернись в меню."
        )
    lines = [f"<b>{escape(title)}</b>", ""]
    for index, place in enumerate(places, start=page * 5 + 1):
        name = escape(clean_title(place.title))
        distance = format_distance_m(place.distance_m)
        address = clamp_text(place.address, 56)
        details = []
        if address:
            details.append(escape(address))
        if distance:
            details.append(escape(distance))
        suffix = f" — {' · '.join(details)}" if details else ""
        lines.append(f"{index}. {name}{suffix}")
    return "\n".join(lines)


def render_place_card(place: BotPlace) -> str:
    emoji, label = CATEGORY_LABELS.get(place.category or "", ("📍", place.category_name or "Место"))
    lines = [f"<b>{emoji} {escape(clean_title(place.title))}</b>", escape(label), ""]
    description = clamp_text(place.short_description, 260)
    if description:
        lines.extend([escape(description), ""])
    if place.address:
        lines.append(f"📍 {escape(place.address)}")
    if place.hours_reliable and place.opening_hours_display:
        lines.append(f"🕐 {escape(place.opening_hours_display)}")
    distance = format_distance_m(place.distance_m)
    if distance:
        lines.append(f"📏 {escape(distance)}")
    return "\n".join(lines).strip()


def render_help() -> str:
    return (
        "<b>Как пользоваться City GO</b>\n\n"
        "• Маршруты — готовые прогулки по городу.\n"
        "• Места рядом — работает после отправки геолокации.\n"
        "• Открыто сейчас — показываем только места с надежными часами.\n"
        "• В карточках нет технических OSM-id и служебных статусов."
    )


def render_error() -> str:
    return "<b>Что-то пошло не так.</b>\n\nПопробуй еще раз или вернись в главное меню."


def _route_meta(route: BotRoute) -> str:
    items = [f"📍 {len(route.points)} точек"]
    duration = format_duration(route.duration_minutes)
    distance = format_distance_km(route.distance_km)
    if duration:
        items.append(f"⏱ {duration}")
    if distance:
        items.append(f"📏 {distance}")
    return " · ".join(items)
