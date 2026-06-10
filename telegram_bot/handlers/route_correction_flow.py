from aiogram.types import Message

from telegram_bot.handlers.route_correction_messages import (
    NO_LOCATION_TEXT,
    NO_ROUTE_TEXT,
)
from telegram_bot.handlers.route_correction_sender import send_corrected_route
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.route_payload import (
    first_route_place_id,
    shortened_time_budget,
)
from telegram_bot.services.route_start import resolve_route_start
from telegram_bot.services.text_intent import TextCorrectionIntent
from telegram_bot.services.user_context import get_user_route


async def answer_route_correction(
    message: Message,
    intent: TextCorrectionIntent,
) -> None:
    if intent.action == "rebuild_from_here":
        await _correct_from_current_start(message)
        return
    await _correct_existing_route(
        message,
        intent.action,
        avoided_categories=intent.avoided_categories,
    )


async def _correct_from_current_start(message: Message) -> None:
    if not message.from_user:
        await _answer_no_route(message)
        return

    route = get_user_route(message.from_user.id)
    if route is None:
        await _answer_no_route(message)
        return

    client = RecommendationApiClient()
    start = await resolve_route_start(message.from_user.id, client)
    if start is None:
        await message.answer(NO_LOCATION_TEXT, reply_markup=get_main_menu_keyboard())
        return

    await send_corrected_route(
        message,
        route,
        "rebuild_from_here",
        current_lat=start.lat,
        current_lng=start.lng,
    )


async def _correct_existing_route(
    message: Message,
    action: str,
    avoided_categories: tuple[str, ...] = (),
) -> None:
    if not message.from_user:
        await _answer_no_route(message)
        return

    route = get_user_route(message.from_user.id)
    if route is None:
        await _answer_no_route(message)
        return

    kwargs = _correction_kwargs(route, action, avoided_categories)
    await send_corrected_route(message, route, action, **kwargs)


def _correction_kwargs(
    route: dict[str, object],
    action: str,
    avoided_categories: tuple[str, ...],
) -> dict[str, object]:
    target = first_route_place_id(route)
    target_kwargs = {"target_place_id": target} if target else {}
    budget_kwargs = (
        {"new_time_budget_minutes": shortened_time_budget(route)}
        if action == "shorten_route"
        else {}
    )
    avoid_kwargs = {"avoided_categories": list(avoided_categories)} if avoided_categories else {}
    return {**target_kwargs, **budget_kwargs, **avoid_kwargs}


async def _answer_no_route(message: Message) -> None:
    await message.answer(NO_ROUTE_TEXT, reply_markup=get_main_menu_keyboard())
