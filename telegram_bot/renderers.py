from __future__ import annotations

from html import escape

from telegram_bot.quality import clean_title
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint
from telegram_bot.utils import compact_text, format_duration, format_km, format_meters

CITY_SELECT_VISIBLE_LIMIT = 5

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
        "<b>City GO</b>\n\n"
        "Городской гид в Telegram: места с фото, открытые точки, маршруты и поиск рядом.\n"
        "Выбери город, и начнём."
    )


def city_select_text(cities: list[BotCity]) -> str:
    if not cities:
        return "<b>Пока нет доступных городов.</b>\n\nКаталог появится здесь после публикации города."

    visible_count = min(len(cities), CITY_SELECT_VISIBLE_LIMIT)
    hidden_count = max(len(cities) - visible_count, 0)
    lines = [
        "<b>Выбери город</b>",
        "",
        f"Доступно: <b>{len(cities)}</b>.",
    ]
    if hidden_count:
        lines.append(f"На кнопках показаны {visible_count}. Ещё {hidden_count} можно найти поиском.")
    lines += [
        "",
        "Нажми город ниже или напиши название сообщением.",
    ]
    return "\n".join(lines)


def main_menu_text(city: BotCity) -> str:
    suffix = f" · {city.places_count} мест" if city.places_count else ""
    return (
        f"<b>🏙 {escape(city.name)}{suffix}</b>\n\n"
        "Что делаем?"
    )


def routes_list_text(city: BotCity, routes: list[BotRoute], page: int) -> str:
    if not routes:
        return (
            f"<b>Маршруты: {escape(city.name)}</b>\n\n"
            "Пока нет готовых прогулок с качественными точками. Можно посмотреть места или собрать временную прогулку из опубликованных точек."
        )
    lines = [f"<b>🚶 Маршруты: {escape(city.name)}</b>", ""]
    for index, route in enumerate(routes, start=page * 5 + 1):
        meta = route_meta(route)
        lines.append(f"{index}. <b>{escape(clean_title(route.title))}</b>" + (f"\n   {escape(meta)}" if meta else ""))
    lines.append("\nВыбери маршрут кнопкой ниже.")
    return "\n".join(lines)


def generated_route_intro_text(city: BotCity, route: BotRoute) -> str:
    return (
        f"<b>Маршруты: {escape(city.name)}</b>\n\n"
        "Готовых прогулок для этого города пока нет. Собрал временную прогулку из опубликованных route-eligible точек.\n\n"
        + route_card_text(route)
    )


def route_card_text(route: BotRoute) -> str:
    lines = [f"<b>🚶 {escape(clean_title(route.title))}</b>", ""]
    meta = route_meta(route)
    if meta:
        lines += [escape(meta), ""]
    description = compact_text(route.short_description, 180)
    if description:
        lines += [escape(description), ""]
    lines.append("<b>Порядок точек</b>")
    for point in route.points[:5]:
        lines.append(f"{point.index + 1}. {escape(clean_title(point.title))}")
    if len(route.points) > 5:
        lines.append(f"…ещё {len(route.points) - 5}")
    lines.append("\nНажми «Начать маршрут», и я поведу по точкам прямо в чате.")
    return "\n".join(lines).strip()


def route_points_text(route: BotRoute) -> str:
    lines = [f"<b>Точки маршрута: {escape(clean_title(route.title))}</b>", ""]
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
        f"<b>{escape(clean_title(route.title))}</b>",
        f"{progress} точка {min(point.index + 1, total)} из {total}",
        f"Посещено: {visited_count}. Пропущено: {skipped_count}.",
        "",
        f"<b>📍 {escape(clean_title(point.title))}</b>",
    ]
    if point.category:
        lines.append(label_for_category(point.category))
    if distance_m is not None:
        lines.append(f"📏 До точки: {escape(format_meters(distance_m) or '')}")
    description = compact_text(point.short_description, 180)
    if description:
        lines += ["", escape(description)]
    if point.address:
        lines.append(f"\n📍 {escape(point.address)}")
    return "\n".join(line for line in lines if line != "")


def route_completed_text(route: BotRoute, visited_count: int) -> str:
    return (
        "<b>Маршрут завершён.</b>\n\n"
        f"{escape(clean_title(route.title))}\n"
        f"Пройдено точек: <b>{visited_count} из {len(route.points)}</b>."
    )


def places_list_text(title: str, places: list[BotPlace], page: int) -> str:
    if not places:
        return f"<b>{escape(title)}</b>\n\nНичего не найдено. Попробуй другую категорию, поиск текстом или вернись в меню."
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
    description = compact_text(place.short_description, 220)
    if description:
        lines += [escape(description), ""]
    if place.hours_reliable and place.opening_hours_display:
        lines.append(f"🟢 Открыто · {escape(place.opening_hours_display)}")
    else:
        lines.append("🟠 Уточнить часы")
    if place.address:
        lines.append(f"📍 {escape(place.address)}")
    distance = format_meters(place.distance_m)
    if distance:
        lines.append(f"📏 {escape(distance)}")
    return "\n".join(lines).strip()


def open_now_empty_text() -> str:
    return (
        "<b>Открыто сейчас</b>\n\n"
        "Сейчас нет мест с надёжными часами работы. Попробуй общий список или поиск."
    )


def open_now_fallback_text(city: BotCity, places: list[BotPlace]) -> str:
    if not places:
        return open_now_empty_text()
    lines = [
        "<b>Открыто сейчас</b>",
        "",
        "Точно открытых прямо сейчас не нашёл. Показываю места с проверенным расписанием, чтобы было что выбрать без мусора.",
        "",
    ]
    for index, place in enumerate(places, start=1):
        details = []
        if place.category:
            details.append(label_for_category(place.category))
        if place.opening_hours_display:
            details.append(place.opening_hours_display)
        suffix = f"\n   {' · '.join(escape(item) for item in details if item)}" if details else ""
        lines.append(f"{index}. <b>{escape(clean_title(place.title))}</b>{suffix}")
    lines.append(f"\nГород: {escape(city.name)}")
    return "\n".join(lines)


def nearby_request_text() -> str:
    return (
        "<b>Места рядом</b>\n\n"
        "Отправь геолокацию через скрепку Telegram, и я покажу ближайшие места. "
        "Если геолокация не сработает, использую центр выбранного города."
    )


def nearby_city_center_text(city: BotCity, places: list[BotPlace]) -> str:
    if not places:
        return (
            f"<b>📍 Рядом: {escape(city.name)}</b>\n\n"
            "Геолокации пока нет, а возле центра города подходящих мест не нашлось. Выбери категорию ниже или отправь геолокацию через скрепку Telegram."
        )
    return (
        f"<b>📍 Рядом: центр города {escape(city.name)}</b>\n\n"
        "Геолокации пока нет, поэтому показываю точки около центра выбранного города.\n\n"
        + places_list_text("Ближайшие места", places, 0)
    )


def no_results_text(query: str) -> str:
    return (
        f"<b>Ничего не найдено</b>\n\n"
        f"По запросу <code>{escape(query)}</code> в каталоге пусто.\n\n"
        "Попробуй проще: парк, музей, кофе, еда."
    )


def help_text() -> str:
    return (
        "<b>Что умеет City GO</b>\n\n"
        "• показывает маршруты и места из опубликованного каталога;\n"
        "• ищет рядом по геолокации;\n"
        "• показывает «Открыто сейчас» только при надёжных часах;\n"
        "• ведёт по маршруту внутри чата;\n"
        "• скрывает технические и служебные точки."
    )


def error_text() -> str:
    return "<b>Что-то пошло не так.</b>\n\nПопробуй ещё раз или вернись в главное меню."


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
    emoji, label = CATEGORY_LABELS.get(category or "", ("📍", "Место"))
    return f"{emoji} {label}"