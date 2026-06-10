from aiogram.types import Message

from telegram_bot.handlers.route_correction_messages import ERROR_TEMPLATE
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.backend_errors import friendly_backend_error
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.route_formatter import format_route_message
from telegram_bot.services.route_payload import route_place_ids
from telegram_bot.services.user_context import save_user_route


async def send_corrected_route(
    message: Message,
    route: dict[str, object],
    action: str,
    **kwargs: object,
) -> None:
    client = RecommendationApiClient()
    result = await client.correct_route(route, action, **kwargs)
    if not result.get("ok"):
        await message.answer(
            ERROR_TEMPLATE.format(
                base_url=result.get("base_url", ""),
                error=friendly_backend_error(result.get("error")),
            )
        )
        return

    updated = result.get("data")
    if not isinstance(updated, dict):
        await message.answer(
            ERROR_TEMPLATE.format(
                base_url=client.base_url,
                error=friendly_backend_error("bad response"),
            )
        )
        return

    if message.from_user:
        save_user_route(message.from_user.id, updated)
    titles = await client.get_place_titles(route_place_ids(updated))
    await message.answer(
        format_route_message(updated, titles),
        reply_markup=get_main_menu_keyboard(),
    )
