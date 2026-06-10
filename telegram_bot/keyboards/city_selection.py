from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CITY_CALLBACK_CODES = {
    "zel": "zelenogradsk",
    "kut": "kutaisi",
    "yvn": "yerevan",
    "khm": "khanty-mansiysk",
}

SLUG_CALLBACK_CODES = {value: key for key, value in CITY_CALLBACK_CODES.items()}


def city_selection_keyboard(cities: list[dict[str, object]]) -> InlineKeyboardMarkup:
    buttons = tuple(map(_button, cities))
    rows = [list(buttons[index:index + 2]) for index in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=[*rows, [_all_button()]])


def city_slug_from_callback(data: str) -> str | None:
    code = data.removeprefix("city:")
    return CITY_CALLBACK_CODES.get(code)


def _button(city: dict[str, object]) -> InlineKeyboardButton:
    slug = str(city.get("slug", ""))
    code = SLUG_CALLBACK_CODES.get(slug, slug[:12])
    suffix = " · готовится" if city.get("launch_status") != "published" else ""
    return InlineKeyboardButton(text=f"{city.get('name', slug)}{suffix}", callback_data=f"city:{code}")


def _all_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🌍 Все города", callback_data="cities:all")
