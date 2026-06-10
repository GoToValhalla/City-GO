from aiogram import Router
from aiogram.types import Message

from telegram_bot.handlers.place_menu.nearby import answer_nearby
from telegram_bot.handlers.place_menu.text_place import answer_place_intent
from telegram_bot.handlers.route import answer_route
from telegram_bot.handlers.route_correction_flow import answer_route_correction
from telegram_bot.handlers.route_correction_messages import NO_ROUTE_TEXT
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.messages import MVP_FALLBACK_TEMPLATE, ONLY_TEXT_MESSAGE
from telegram_bot.services.event_log import log_telegram_event
from telegram_bot.services.text_intent import (
    TextCorrectionIntent,
    parse_text_correction_intent,
    parse_text_nearby_intent,
    parse_text_place_intent,
    parse_text_route_intent,
)
from telegram_bot.services.user_context import get_user_route

router = Router()


@router.message()
async def fallback_message_handler(message: Message) -> None:
    user_text = (message.text or "").strip()
    user_id = message.from_user.id if message.from_user else None
    log_telegram_event(user_id, "message_received", payload={"text": user_text})

    if not user_text:
        await message.answer(
            ONLY_TEXT_MESSAGE,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    correction = parse_text_correction_intent(user_text)
    if correction is not None:
        log_telegram_event(user_id, "correction_intent", payload={"action": correction.action})
        await _answer_correction_or_no_route(message, correction)
        return

    route_intent = parse_text_route_intent(user_text)
    if route_intent is not None:
        log_telegram_event(user_id, "route_intent", payload={"city_query": route_intent.city_query or ""})
        await answer_route(message, route_intent)
        return

    nearby_intent = parse_text_nearby_intent(user_text)
    if nearby_intent is not None:
        log_telegram_event(user_id, "nearby_intent", payload={"city_query": nearby_intent.city_query or ""})
        await answer_nearby(message, nearby_intent.city_query)
        return

    place_intent = parse_text_place_intent(user_text)
    if place_intent is not None:
        log_telegram_event(user_id, "place_intent", payload={"kind": place_intent.kind})
        await answer_place_intent(message, place_intent)
        return

    log_telegram_event(user_id, "fallback")
    await message.answer(
        MVP_FALLBACK_TEMPLATE.format(user_text=user_text),
        reply_markup=get_main_menu_keyboard(),
    )


async def _answer_correction_or_no_route(
    message: Message,
    correction: TextCorrectionIntent,
) -> None:
    if not message.from_user or get_user_route(message.from_user.id) is None:
        await message.answer(NO_ROUTE_TEXT, reply_markup=get_main_menu_keyboard())
        return
    await answer_route_correction(message, correction)
