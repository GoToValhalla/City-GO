from __future__ import annotations

from html import escape

from telegram_bot.quality import clean_title
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint
from telegram_bot.utils import compact_text, format_duration, format_km, format_meters

CATEGORY_LABELS = {
    "culture": ("🏛", "Культура"),
    "museum": ("🏛", "Музей"),
    "park": ("🌿", "Парк"),
    "walk": ("🚶", "Прогулка"),
    "viewpoint": ("👀", "Смотровая точка"),
    "food": ("🍽", "Еда"),
    "restaurant": ("🍽", "Ресторан"),
    "bar": ("🍸", "Бар"),
    "bakery": ("🥐", "Пекарня"),
    "coffee": ("☕", "Кофе"),
    "cafe": ("☕", "Кофе"),
    "hotel": ("🏨", "Проживание"),
    "beach": ("🌊", "Пляж"),
    "attraction": ("👀", "Достопримечательность"),
    "landmark": ("👀", "Достопримечательность"),
    "historic": ("🏛", "Историческое место"),
    "monument": ("🏛", "Памятник"),
}


def start_text() -> str:
    return (
        "<b>Привет! Я City GO.</b>\n\n"
        "Покажу маршруты, интересные места, кафе и точки рядом.\n"
        "Выбери город, и начнем."
    )


def city_select_text(cities: list[BotCity]) -> str:
    if not cities:
        return "<b>Пока нет доступных городов.</b>\n\nВ админке нет активных городов с публичным статусом."
    return "<b>Выбери город</b>\n\nПокажу только опубликованный каталог без технических OSM-точек."


def main_menu_text(city: BotCity) -> str:
    suffix = f" · {city.places_count} мест" if city.places_count else ""
    return f"<b>🏙 {escape(city.name)}{suffix}</b>\n\nЧто хочешь найти?"


def routes_list_text(city: BotCity, routes: list[BotRoute], page: int) -> str:
    if not routes:
        return f"<b>Маршруты для города {escape(city.name)} пока не готовы.</b>\n\nПоказываю только маршруты, где осталось минимум две качественные точки. Попробуй места или кафе."
    lines = [f"<b>🚶 Маршруты: {escape(city.name)}</b>", ""]
    for index, route in enumerate(routes, start=page * 5 + 1):
        meta = route_meta(route)
        lines.append(f"{index}. <b>{escape(route.title)}</b>" + (f"\n   {escape(meta)}" if meta else ""))
    lines.append("\nВыбери маршрут кнопкой ниже.")
    return "\n".join(lines)


def route_card_text(route: BotRoute) -> str:
    lines = [f"<b>🚶 {escape(route.title)}</b>", ""]
    description = compact_text(route.short_description, 260)
    if description:
        lines += [escape(description), ""]
    meta = route_meta(route)
    if meta:
        lines += [escape(meta), ""]
    lines.append("<b>Первые точки:</b>")
    for point in route.points[:5]:
        lines.append(f"{point.index + 1}. {escape(clean_title(point.title))}")
    if len(route.points) > 5:
        lines.append(f"…еще {len(route.points) - 5}")
    lines.append("\nНажми «Начать маршрут», и я буду вести по точкам в этом сообщении.")
    return "\n".join(lines).strip()


def route_points_text(route: BotRoute) -> str:
    lines = [f"<b>Точки маршрута: {escape(route.title)}</b>", ""]
    for point in route.points:
        details = [label_for_category(point.category)] if point.category else []
        if point.address:
            details.append(compact_text(point.address, 70) or "")
        suffix = f" — {escape(' · '.join(item for item in details if item))}" if details else ""
        lines.append(f"{point.index + 1}. {escape(clean_title(point.title))}{suffix}")
    return "\n".join(lines)


def route_step_text(route: BotRoute, point: BotRoutePoint, visited_count: int, distance_m: int | None = None, skipped_count: int = 0) -> str:
    total = len(route.points)
    done_count = min(visited_count + skipped_count, total)
    progress = "▓" * done_count + "░" * max(total - done_count, 0)
    lines = [
        f"<b>{escape(route.title)}</b>",
        f"{progress} точка {min(point.index + 1, total)} из {total}",
        f"Посещено: {visited_count}. Пропущено: {skipped_count}.",
        "",
        f"<b>📍 {escape(clean_title(point.title))}</b>",
    ]
    if point.category:
        lines.append(label_for_category(point.category))
    if distance_m is not None:
        lines.append(f"📏 До точки: {escape(format_meters(distance_m) or '')}")
    description = compact_text(point.short_description, 260)
    if description:
        lines += ["", escape(description)]
    if point.address:
        lines.append(f"\n📍 {escape(point.address)}")
    return "\n".join(line for line in lines if line != "")


def route_completed_text(route: BotRoute, visited_count: int) -> str:
    return (
        "<b>Маршрут завершен.</b>\n\n"
        f"{escape(route.title)}\n"
        f"Пройдено точек: <b>{visited_count} из {len(route.points)}</b>."
    )


def places_list_text(title: str, places: list[BotPlace], page: int) -> str:
    if not places:
        return f"<b>{escape(title)}</b>\n\nНичего не нашлось. Попробуй другую категорию, поиск текстом или вернись в меню."
    lines = [f"<b>{escape(title)}</b>", ""]
    for index, place in enumerate(places, start=page * 5 + 1):
        details = []
        if place.category:
            details.append(label_for_category(place.category))
        distance = format_meters(place.distance_m)
        if distance:
            details.append(distance)
        if place.address:
            details.append(compact_text(place.address, 56) or "")
        suffix = f"\n   {' · '.join(escape(item) for item in details if item)}" if details else ""
        lines.append(f"{index}. <b>{escape(clean_title(place.title))}</b>{suffix}")
    lines.append("\nОткрой карточку места кнопкой ниже.")
    return "\n".join(lines)


def place_card_text(place: BotPlace) -> str:
    emoji, label = CATEGORY_LABELS.get(place.category or "", ("📍", place.category_name or "Место"))
    lines = [f"<b>{emoji} {escape(clean_title(place.title))}</b>", escape(label), ""]
    description = compact_text(place.short_description, 280)
    if description:
        lines += [escape(description), ""]
    if place.address:
        lines.append(f"📍 {escape(place.address)}")
    if place.hours_reliable and place.opening_hours_display:
        lines.append(f"🕐 {escape(place.opening_hours_display)}")
    distance = format_meters(place.distance_m)
    if distance:
        lines.append(f"📏 {escape(distance)}")
    return "\n".join(lines).strip()


def open_now_empty_text() -> str:
    return (
        "<b>Открыто сейчас</b>\n\n"
        "Показываю только места с проверенными часами. Сейчас таких мест мало или они закрыты."
    )


def nearby_request_text() -> str:
    return (
        "<b>Места рядом</b>\n\n"
        "Чтобы показать ближайшие места, отправь геолокацию через скрепку/вложение Telegram. "
        "Если Telegram не дает отправить геолокацию, выбери готовый раздел ниже."
    )


def no_results_text(query: str) -> str:
    return (
        f"<b>Ничего не нашлось</b>\n\n"
        f"По запросу <code>{escape(query)}</code> в каталоге пусто.\n\n"
        "Попробуй более общий запрос: парк, музей, кофе, еда."
    )


def help_text() -> str:
    return (
        "<b>Что умеет бот</b>\n\n"
        "• показывает города, маршруты и места из опубликованного каталога;\n"
        "• ищет рядом по геолокации;\n"
        "• показывает только надежное «открыто сейчас»;\n"
        "• ведет по маршруту внутри чата;\n"
        "• скрывает технические OSM-id, служебные категории и debug-поля."
    )


def error_text() -> str:
    return "<b>Что-то пошло не так.</b>\n\nПопробуй еще раз или вернись в главное меню."


def route_meta(route: BotRoute) -> str:
    items = [f"📍 {len(route.points)} точек"]
    duration = format_duration(route.duration_minutes)
    distance = format_km(route.distance_km)
    if duration:
        items.append(f"⏱ {duration}")
    if distance:
        items.append(f"📏 {distance}")
    return " · ".join(items)


def label_for_category(category: str | None) -> str:
    emoji, label = CATEGORY_LABELS.get(category or "", ("📍", category or "Место"))
    return f"{emoji} {label}"
