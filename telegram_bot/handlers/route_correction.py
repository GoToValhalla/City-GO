from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.handlers.route_correction_flow import answer_route_correction
from telegram_bot.services.text_intent import TextCorrectionIntent

router = Router()


@router.message(F.text == "Убрать первую точку")
async def remove_first_point_handler(message: Message) -> None:
    await answer_route_correction(message, TextCorrectionIntent("remove_place"))


@router.message(F.text == "Маршрут короче")
async def shorten_route_handler(message: Message) -> None:
    await answer_route_correction(message, TextCorrectionIntent("shorten_route"))


@router.message(F.text == "Перестроить отсюда")
async def rebuild_from_here_handler(message: Message) -> None:
    await answer_route_correction(message, TextCorrectionIntent("rebuild_from_here"))


@router.message(F.text == "Не хочу такой тип")
async def avoid_first_category_handler(message: Message) -> None:
    await answer_route_correction(message, TextCorrectionIntent("avoid_category"))


@router.message(F.text == "Добавить точку")
@router.message(F.text == "Маршрут длиннее")
async def extend_route_handler(message: Message) -> None:
    await answer_route_correction(message, TextCorrectionIntent("extend_route"))
