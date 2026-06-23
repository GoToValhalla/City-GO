from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Update

from core.config import settings
from telegram_bot.handlers.catalog import router as catalog_router

logger = logging.getLogger(__name__)


class SoftRateLimitMiddleware(BaseMiddleware):
    def __init__(self, max_events: int = 30, window_seconds: int = 60) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        now = time.monotonic()
        values = [item for item in self._events[user.id] if now - item <= self.window_seconds]
        if len(values) >= self.max_events:
            return None
        values.append(now)
        self._events[user.id] = values
        return await handler(event, data)


def create_bot() -> Bot:
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN пустой. Заполни его в .env перед запуском Telegram-бота.")
    return Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(SoftRateLimitMiddleware())
    dp.callback_query.middleware(SoftRateLimitMiddleware())
    dp.include_router(catalog_router)
    return dp


async def feed_webhook_update(bot: Bot, update_payload: dict[str, object]) -> None:
    update = Update.model_validate(update_payload)
    dp = create_dispatcher()
    await dp.feed_update(bot, update)


async def run_polling() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    bot = create_bot()
    dp = create_dispatcher()
    logger.info("Telegram bot is starting...")
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())
