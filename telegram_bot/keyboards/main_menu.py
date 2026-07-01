"""
Клавиатуры главного меню для Telegram-бота City GO.

ReplyKeyboard используется только там, где Telegram требует нативный запрос геолокации.
Основное меню должно быть inline-only, чтобы старая большая клавиатура не залипала у пользователя.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def get_main_menu_keyboard() -> ReplyKeyboardRemove:
    """Legacy compatibility: never send persistent main-menu reply keyboard again."""
    return ReplyKeyboardRemove()


def get_location_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геопозицию", request_location=True)],
            [KeyboardButton(text="Использовать центр города")],
            [KeyboardButton(text="Сменить город")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выберите способ определить старт",
    )
