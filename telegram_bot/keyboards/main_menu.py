"""
Клавиатуры главного меню для Telegram-бота City GO.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Возвращает основную reply-клавиатуру lite-бота.

    Бот не дублирует web, а закрывает быстрые сценарии:
    маршрут, места рядом, открыто сейчас, поиск, смена города.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗺 Построить маршрут"), KeyboardButton(text="📍 Места")],
            [KeyboardButton(text="📡 Отправить геолокацию", request_location=True)],
            [KeyboardButton(text="☕ Открыто сейчас"), KeyboardButton(text="🔎 Найти место")],
            [KeyboardButton(text="⚙️ Сменить город"), KeyboardButton(text="ℹ️ Что умеет бот")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Например: маршрут на 2 часа с кофе",
    )
