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
from aiogram.types import BotCommand, CallbackQuery, Message, TelegramObject, Update

from core.config import settings
from telegram_bot.handlers.admin_moderation import router as admin_moderation_router
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
            await _send_rate_limit_notice(event)
            return None
        values.append(now)
        self._events[user.id] = values
        return await handler(event, data)


def create_bot() -> Bot:
    token = _bot_token()
    if not token:
        raise ValueError("BOT_TOKEN/TELEGRAM_BOT_TOKEN пустой. Заполни токен в .env перед запуском Telegram-бота.")
    _validate_mini_app_config()
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def _validate_mini_app_config() -> None:
    # tma_enabled feature toggle defaults ON (project rule: non-AI toggles
    # default ON), so in production the Mini App URL must always be valid,
    # not only when a DB row happens to enable the toggle.
    if settings.app_env != "production":
        return
    url = settings.telegram_mini_app_url.strip()
    if not url.startswith("https://"):
        raise ValueError(
            "TELEGRAM_MINI_APP_URL пустой или некорректный (должен начинаться с https://). "
            "Заполни переменную в .env перед запуском Telegram-бота в production."
        )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(SoftRateLimitMiddleware())
    dp.callback_query.middleware(SoftRateLimitMiddleware())
    dp.include_router(admin_moderation_router)
    dp.include_router(catalog_router)
    return dp


async def setup_bot_commands(bot: Bot) -> None:
    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Запустить City GO"),
                BotCommand(command="menu", description="Открыть главное меню"),
                BotCommand(command="moderation", description="Модерация мест"),
                BotCommand(command="help", description="Помощь и возможности"),
            ]
        )
    except Exception:
        logger.warning("Failed to register Telegram bot commands", exc_info=True)


async def feed_webhook_update(bot: Bot, update_payload: dict[str, object]) -> None:
    update = Update.model_validate(update_payload)
    dp = create_dispatcher()
    await dp.feed_update(bot, update)


async def run_polling() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    bot = create_bot()
    dp = create_dispatcher()
    await setup_bot_commands(bot)
    logger.info("Telegram bot is starting...")
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_polling())


def _bot_token() -> str:
    return settings.bot_token or settings.telegram_bot_token


async def _send_rate_limit_notice(event: TelegramObject) -> None:
    text = "Не так быстро. Подожди пару секунд и нажми снова."
    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=False)
        return
    if isinstance(event, Message):
        await event.answer(text)
