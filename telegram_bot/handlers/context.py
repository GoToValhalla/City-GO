from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.context_summary import format_context_snapshot
from telegram_bot.services.user_context import (
    get_user_context_snapshot,
    reset_user_context,
)

router = Router()

_NO_USER_TEXT = "<b>Не удалось определить пользователя</b>"
_RESET_TEXT = "<b>Контекст сброшен</b>\n\nМожно начать новый маршрут."


@router.message(Command("context"))
@router.message(F.text == "Мой контекст")
async def context_handler(message: Message) -> None:
    if not message.from_user:
        await message.answer(_NO_USER_TEXT, reply_markup=get_main_menu_keyboard())
        return

    snapshot = get_user_context_snapshot(message.from_user.id)
    await message.answer(
        format_context_snapshot(snapshot),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("reset_context"))
@router.message(F.text == "Сбросить контекст")
async def reset_context_handler(message: Message) -> None:
    if not message.from_user:
        await message.answer(_NO_USER_TEXT, reply_markup=get_main_menu_keyboard())
        return

    reset_user_context(message.from_user.id)
    await message.answer(_RESET_TEXT, reply_markup=get_main_menu_keyboard())
