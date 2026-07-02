"""LEGACY TELEGRAM ROUTE HANDLER.

Status: not included in `telegram_bot.main.create_dispatcher()`.

Active Telegram routers:
- `telegram_bot.handlers.admin_moderation`
- `telegram_bot.handlers.catalog`

Rules:
- Do not add new Telegram route actions here.
- Do not re-register this router without a dedicated Telegram route migration task.
- Keep only as historical implementation of the old `/route` bot flow.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.keyboards.route_actions import get_route_actions_keyboard
from telegram_bot.services.backend_errors import friendly_backend_error
from telegram_bot.services.city_fallback import unsupported_city_message
from telegram_bot.services.event_log import log_telegram_event
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.route_formatter import format_route_message
from telegram_bot.services.route_payload import route_place_ids
from telegram_bot.services.route_start import resolve_route_start
from telegram_bot.services.text_intent import TextRouteIntent
from telegram_bot.services.user_context import get_user_city, save_user_route

router = Router()

_NO_START_TEXT = (
    "<b>Не удалось определить старт</b>\n\n"
    "Нажмите <b>📡 Отправить геолокацию</b> или выберите город — тогда построю маршрут от центра."
)

_DEFAULT_INTENT = TextRouteIntent(minutes=120, interests=(), avoided_categories=())

_ERROR_TEMPLATE = (
    "<b>Маршрут не собрался</b>\n\n"
    "Причина: <b>{error}</b>\n\n"
    "Что можно сделать:\n"
    "• отправить геолокацию;\n"
    "• увеличить время маршрута;\n"
    "• сменить город;\n"
    "• открыть список мест."
)


@router.message(Command("route"))
@router.message(F.text == "Собрать маршрут")
@router.message(F.text == "🗺 Построить маршрут")
async def build_route_handler(message: Message) -> None:
    await answer_route(message, _DEFAULT_INTENT)


async def answer_route(message: Message, intent: TextRouteIntent) -> None:
    if not message.from_user:
        await message.answer(_NO_START_TEXT, reply_markup=get_main_menu_keyboard())
        return

    client = RecommendationApiClient()
    user_id = message.from_user.id
    selected_city = get_user_city(user_id)
    if selected_city is None:
        await prompt_city(message)
        return
    fallback = await unsupported_city_message(client, intent.city_query)
    if fallback is not None:
        log_telegram_event(user_id, "unsupported_city", payload={"city_query": intent.city_query or ""})
        await message.answer(fallback, reply_markup=get_main_menu_keyboard())
        return

    log_telegram_event(user_id, "route_build_started", payload={"minutes": intent.minutes})
    start = await resolve_route_start(user_id, client, city_query=intent.city_query)
    if start is None:
        await message.answer(_NO_START_TEXT, reply_markup=get_main_menu_keyboard())
        return

    await message.answer(f"{_loading_text(intent)}\nСтарт: <b>{start.label}</b>", reply_markup=get_main_menu_keyboard())

    result = await client.build_route(
        lat=start.lat,
        lng=start.lng,
        minutes=intent.minutes,
        interests=intent.interests,
        avoided_categories=intent.avoided_categories,
        city_slug=selected_city,
        start_source=_api_start_source(start.source),
    )
    if not result.get("ok"):
        log_telegram_event(user_id, "route_build_failed", payload={"error": str(result.get("error", ""))})
        await message.answer(
            _ERROR_TEMPLATE.format(error=friendly_backend_error(result.get("error"))),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    route = result.get("data")
    if not isinstance(route, dict):
        log_telegram_event(user_id, "route_build_failed", payload={"error": "bad response"})
        await message.answer(_ERROR_TEMPLATE.format(error=friendly_backend_error("bad response")), reply_markup=get_main_menu_keyboard())
        return

    save_user_route(user_id, route)
    log_telegram_event(
        user_id,
        "route_build_succeeded",
        payload={
            "route_id": str(route.get("route_id", "")),
            "quality_status": str(route.get("quality_status", "")),
            "points": len(route.get("points", [])) if isinstance(route.get("points"), list) else 0,
        },
    )
    place_ids = route_place_ids(route)
    titles = await client.get_place_titles(place_ids)
    await message.answer(format_route_message(route, titles), reply_markup=get_route_actions_keyboard())


def _api_start_source(source: str) -> str:
    if source == "user_location":
        return "current_location"
    if source in {"manual_address", "text_city"}:
        return "address"
    return "city_center"


def _loading_text(intent: TextRouteIntent) -> str:
    hours = intent.minutes / 60
    duration = f"{hours:g} ч" if intent.minutes % 60 == 0 else f"{intent.minutes} мин"
    return f"Собираю маршрут на {duration}..."
