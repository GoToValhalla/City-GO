"""
Клавиатуры главного меню для Telegram-бота City GO.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from core.config import settings


def _mini_app_button() -> KeyboardButton | None:
    url = (settings.telegram_mini_app_url or "").strip()
    if not url.startswith("https://"):
        return None
    return KeyboardButton(text="🌐 Открыть City GO", web_app=WebAppInfo(url=url))


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Возвращает основную reply-клавиатуру lite-бота.

    Бот закрывает быстрые сценарии, а при настроенном HTTPS Mini App
    даёт вход в полноценный интерфейс City GO внутри Telegram.
    """
    keyboard = [
        [KeyboardButton(text="🗺 Построить маршрут"), KeyboardButton(text="📍 Места")],
        [KeyboardButton(text="📡 Отправить геолокацию", request_location=True)],
        [KeyboardButton(text="☕ Открыто сейчас"), KeyboardButton(text="🔎 Найти место")],
        [KeyboardButton(text="⚙️ Сменить город"), KeyboardButton(text="ℹ️ Что умеет бот")],
    ]
    mini_app = _mini_app_button()
    if mini_app is not None:
        keyboard.insert(0, [mini_app])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Например: маршрут на 2 часа с кофе",
    )