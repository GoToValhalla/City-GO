from telegram_bot.keyboards.city_selection import city_selection_keyboard
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient

CITY_REQUIRED_TEXT = (
    "<b>Выберите город</b>\n"
    "После этого покажу маршруты, места и быстрый поиск именно по нему."
)
CITY_READY_TEXT = (
    "<b>{city_name}</b>\n"
    "Мест в каталоге: <b>{places_count}</b>\n\n"
    "Что сделаем сейчас?"
)
CITY_DRAFT_TEXT = (
    "<b>Город пока готовится</b>\n"
    "Каталог ещё не прошёл проверку покрытия. Можно выбрать другой город."
)


async def city_selection_markup(client: CityGoApiClient | None = None):
    cities = await available_city_items(client or CityGoApiClient(), include_draft=True)
    return city_selection_keyboard(cities)


async def available_city_items(client: CityGoApiClient, include_draft: bool = False) -> list[dict[str, object]]:
    result = await client.get_available_cities(include_draft=include_draft)
    items = result.get("items") if isinstance(result, dict) else None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def city_by_slug(cities: list[dict[str, object]], slug: str) -> dict[str, object] | None:
    return next(filter(lambda city: city.get("slug") == slug, cities), None)


def city_main_menu_text(city: dict[str, object]) -> str:
    return CITY_READY_TEXT.format(
        city_name=city.get("name", city.get("slug", "")),
        places_count=int(city.get("places_count") or 0),
    )


def main_menu_for_city():
    return get_main_menu_keyboard()