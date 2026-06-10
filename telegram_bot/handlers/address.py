"""
Хендлер ручного ввода адреса для Telegram-бота City GO.

Текущая логика:
- пользователь нажимает кнопку "Ввести адрес"
- бот переходит в состояние ожидания адреса
- пользователь отправляет адрес текстом
- бот сохраняет адрес в памяти процесса

Пока без геокодинга.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.address_context import save_user_address
from telegram_bot.services.address_messages import (
    ADDRESS_CANCELLED_TEXT,
    ADDRESS_EMPTY_TEXT,
    ADDRESS_HINT_TEXT,
    ADDRESS_SAVED_TEMPLATE,
)
from telegram_bot.states.address_state import AddressInputState


router = Router()


@router.message(F.text == "Ввести адрес")
async def manual_address_entry_handler(message: Message, state: FSMContext) -> None:
    """
    Вход в сценарий ручного ввода адреса.
    """
    await state.set_state(AddressInputState.waiting_for_address)

    await message.answer(
        ADDRESS_HINT_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(
    AddressInputState.waiting_for_address,
    F.text.in_({"Отмена", "отмена", "/cancel"}),
)
async def manual_address_cancel_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Отмена сценария ручного ввода адреса.
    """
    await state.clear()

    await message.answer(
        ADDRESS_CANCELLED_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(AddressInputState.waiting_for_address)
async def manual_address_value_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Принимает адрес пользователя в виде текста.
    """
    raw_address = (message.text or "").strip()

    if not raw_address:
        await message.answer(
            ADDRESS_EMPTY_TEXT,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    if message.from_user:
        save_user_address(
            user_id=message.from_user.id,
            raw_address=raw_address,
        )

    await state.clear()

    await message.answer(
        ADDRESS_SAVED_TEMPLATE.format(raw_address=raw_address),
        reply_markup=get_main_menu_keyboard(),
    )
