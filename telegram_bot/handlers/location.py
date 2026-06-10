"""
Хендлер геолокации для Telegram-бота City GO.
"""

from aiogram import Router
from aiogram.types import Message

from telegram_bot.handlers.place_menu.common import build_result_lines
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.backend_errors import friendly_backend_error
from telegram_bot.services.messages import BACKEND_ERROR_TEMPLATE
from telegram_bot.services.place_messages import (
    NEARBY_EMPTY_TEMPLATE,
    NEARBY_RESULT_HEADER_TEMPLATE,
)
from telegram_bot.services.user_context import save_user_location


router = Router()


@router.message(lambda message: message.location is not None)
async def location_handler(message: Message) -> None:
    """
    Принимает геолокацию пользователя, сохраняет ее
    и запрашивает nearby places.
    """
    if not message.location:
        await message.answer(
            "Не удалось получить геолокацию.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lat = message.location.latitude
    lng = message.location.longitude
    radius_km = 3.0

    if message.from_user:
        save_user_location(
            user_id=message.from_user.id,
            lat=lat,
            lng=lng,
        )

    client = CityGoApiClient()
    result = await client.get_nearby_places(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=friendly_backend_error(result.get("error")),
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

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

    lines = build_result_lines(
        header=NEARBY_RESULT_HEADER_TEMPLATE.format(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        ),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )
