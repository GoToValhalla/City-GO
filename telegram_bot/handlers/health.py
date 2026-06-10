"""Health and help handlers for Telegram bot."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient

router = Router()

HELP_TEXT = (
    "<b>City Go бот</b>\n\n"
    "Быстрые действия:\n"
    "🗺 маршрут\n"
    "📡 старт от геолокации\n"
    "📍 места в городе\n"
    "☕ открыто сейчас\n"
    "🔎 поиск места\n"
    "⚙️ смена города\n\n"
    "Можно писать текстом: маршрут на 2 часа, маршрут на 4 часа с кофе."
)


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Что умеет бот")
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=get_main_menu_keyboard())


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    """Проверяет состояние backend через API client."""
    client = CityGoApiClient()
    result = await client.get_health()

    if result["ok"]:
        await message.answer(
            (
                "<b>Проверка backend</b>\n\n"
                f"Статус: <b>{result['status']}</b>\n"
                f"URL: <b>{result['base_url']}</b>"
            )
        )
        return

    await message.answer(
        (
            "<b>Проверка backend</b>\n\n"
            "Backend сейчас недоступен.\n"
            f"URL: <b>{result['base_url']}</b>\n"
            f"Ошибка: <b>{result['error']}</b>"
        )
    )
