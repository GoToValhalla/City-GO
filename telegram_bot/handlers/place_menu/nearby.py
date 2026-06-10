from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.handlers.place_menu.common import (
    answer_backend_error,
    build_result_lines,
    result_items,
    result_ok,
)
from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.city_fallback import unsupported_city_message
from telegram_bot.services.event_log import log_telegram_event
from telegram_bot.services.messages import NEARBY_STUB_TEXT
from telegram_bot.services.nearby_start import resolve_nearby_start
from telegram_bot.services.place_messages import (
    NEARBY_EMPTY_TEMPLATE,
    NEARBY_RESULT_HEADER_TEMPLATE,
)
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.user_context import get_user_city

router = Router()


@router.message(F.text == "Что рядом")
async def nearby_handler(message: Message) -> None:
    await answer_nearby(message, None)


async def answer_nearby(message: Message, city_query: str | None) -> None:
    if not message.from_user:
        await _answer_stub(message)
        return
    if get_user_city(message.from_user.id) is None:
        await prompt_city(message)
        return

    client = RecommendationApiClient()
    fallback = await unsupported_city_message(client, city_query)
    if fallback is not None:
        log_telegram_event(message.from_user.id, "unsupported_city", payload={"city_query": city_query or ""})
        await message.answer(fallback, reply_markup=get_main_menu_keyboard())
        return

    start = await resolve_nearby_start(
        message.from_user.id,
        client,
        city_query,
    )

    if start is None:
        await _answer_stub(message)
        return

    lat = start.lat
    lng = start.lng
    radius_km = 3.0
    result = await CityGoApiClient().get_nearby_places(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )

    if not result_ok(result):
        await answer_backend_error(message, result)
        return

    items = result_items(result)

    if not items:
        await message.answer(
            NEARBY_EMPTY_TEMPLATE.format(
                lat=lat,
                lng=lng,
                radius_km=radius_km,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await message.answer(
        "\n".join(
            build_result_lines(
                header=NEARBY_RESULT_HEADER_TEMPLATE.format(
                    lat=lat,
                    lng=lng,
                    radius_km=radius_km,
                ),
                items=items,
            )
        ),
        reply_markup=get_main_menu_keyboard(),
    )


async def _answer_stub(message: Message) -> None:
    await message.answer(
        NEARBY_STUB_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )
