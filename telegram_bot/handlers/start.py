"""
Стартовые хендлеры Telegram-бота City GO.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.city_selection import available_city_items, city_by_slug, city_main_menu_text
from telegram_bot.services.messages import (
    HELP_TEXT,
    MAIN_MENU_REOPENED,
    WELCOME_TEXT,
)
from telegram_bot.services.user_context import get_user_city


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Обрабатывает команду /start.
    """
    if not message.from_user:
        await prompt_city(message)
        return
    slug = get_user_city(message.from_user.id)
    cities = await available_city_items(CityGoApiClient(), include_draft=False)
    city = city_by_slug(cities, slug or "")
    if city is None:
        await prompt_city(message)
        return
    await message.answer(city_main_menu_text(city), reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Обрабатывает команду /help.
    """
    await message.answer(
        HELP_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Помощь")
async def help_button_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Помощь'.
    """
    await cmd_help(message)


@router.message(F.text == "Главное меню")
async def main_menu_button_handler(message: Message) -> None:
    """
    Повторно показывает главное меню.
    """
    await message.answer(
        MAIN_MENU_REOPENED,
        reply_markup=get_main_menu_keyboard(),
    )
