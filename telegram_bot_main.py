"""
Отдельная точка входа для Telegram-бота City GO.

Важно:
- этот файл НЕ заменяет текущий main.py FastAPI;
- backend и bot живут отдельно;
- позже бот можно будет подключить к существующим services / api.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from telegram_bot.handlers.address import router as address_router
from telegram_bot.handlers.city_selection import router as city_selection_router
from telegram_bot.handlers.context import router as context_router
from telegram_bot.handlers.free_text import router as free_text_router
from telegram_bot.handlers.health import router as health_router
from telegram_bot.handlers.location import router as location_router
from telegram_bot.handlers.menu import router as menu_router
from telegram_bot.handlers.route import router as route_router
from telegram_bot.handlers.route_correction import router as route_correction_router
from telegram_bot.handlers.start import router as start_router


async def main() -> None:
    """
    Основной запуск Telegram-бота.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not settings.bot_token:
        raise ValueError(
            "BOT_TOKEN пустой. Заполни его в .env перед запуском Telegram-бота."
        )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Порядок важен:
    # 1. health-команды
    # 2. контекст пользователя
    # 3. геолокация
    # 4. маршрут
    # 5. ручной ввод адреса
    # 6. кнопки меню
    # 7. стартовые команды
    # 8. fallback свободного текста
    dp.include_router(health_router)
    dp.include_router(context_router)
    dp.include_router(city_selection_router)
    dp.include_router(location_router)
    dp.include_router(route_router)
    dp.include_router(route_correction_router)
    dp.include_router(address_router)
    dp.include_router(menu_router)
    dp.include_router(start_router)
    dp.include_router(free_text_router)

    logging.info("Telegram bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped manually.")
