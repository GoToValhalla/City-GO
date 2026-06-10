from collections.abc import Awaitable, Callable

from aiogram.types import Message

from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.handlers.place_menu.common import answer_city_result, answer_loading, result_items, result_ok
from telegram_bot.services import place_messages as place_texts
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.city_fallback import unsupported_city_message
from telegram_bot.services.event_log import log_telegram_event
from telegram_bot.services.messages import (
    COFFEE_LOADING_TEXT,
    DOG_FRIENDLY_LOADING_TEXT,
    FOOD_LOADING_TEXT,
    OPEN_NOW_LOADING_TEXT,
    WALKS_LOADING_TEXT,
)
from telegram_bot.services.place_city_context import resolve_place_city_slug
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.text_intent import TextPlaceIntent

Fetcher = Callable[[CityGoApiClient, str], Awaitable[dict[str, object]]]


async def answer_place_intent(message: Message, intent: TextPlaceIntent) -> None:
    rec_client = RecommendationApiClient()

    # Проверяем неподдерживаемый город только если пользователь явно написал город.
    # Простые запросы вроде "Кофе", "Ресторан", "Парк" не должны проверяться как город.
    fallback = await unsupported_city_message(rec_client, intent.city_query)
    if fallback is not None:
        user_id = message.from_user.id if message.from_user else None
        log_telegram_event(
            user_id,
            "unsupported_city",
            payload={"city_query": intent.city_query or ""},
        )
        await message.answer(fallback)
        return

    await answer_loading(message, _LOADING_TEXTS[intent.kind])

    client = CityGoApiClient()
    city_slug = await _city_slug(message, intent, rec_client)

    if city_slug is None:
        await prompt_city(message)
        return

    result = await _fetch_result(client, intent, city_slug)

    if result_ok(result) and not result_items(result):
        await _create_missing_place(
            message=message,
            client=client,
            city_slug=city_slug,
            name=intent.search_query,
        )

    await answer_city_result(
        message,
        result,
        _EMPTY_TEMPLATES[intent.kind],
        _HEADER_TEMPLATES[intent.kind],
        city_slug,
    )


async def _city_slug(
    message: Message,
    intent: TextPlaceIntent,
    rec_client: RecommendationApiClient,
) -> str | None:
    if message.from_user is None:
        return None

    return await resolve_place_city_slug(
        message.from_user.id,
        rec_client,
        intent.city_query,
    )


async def _fetch_result(
    client: CityGoApiClient,
    intent: TextPlaceIntent,
    city_slug: str,
) -> dict[str, object]:
    return await _FETCHERS[intent.kind](client, city_slug)


async def _create_missing_place(
    message: Message,
    client: CityGoApiClient,
    city_slug: str,
    name: str,
) -> None:
    user_id = message.from_user.id if message.from_user else None

    await client.create_discovery_request(
        city_slug=city_slug,
        name=name,
        telegram_user_id=user_id,
    )

    await message.answer(
        "Пока не нашёл это место в опубликованном каталоге. "
        "Я добавил запрос на проверку: каталог может быть покрыт не полностью."
    )


_FETCHERS: dict[str, Fetcher] = {
    "open_now": lambda client, slug: client.get_open_now_places(slug),
    "coffee": lambda client, slug: client.get_coffee_places(slug),
    "food": lambda client, slug: client.get_food_places(slug),
    "walks": lambda client, slug: client.get_walk_places(slug),
    "dog_friendly": lambda client, slug: client.get_dog_friendly_places(slug),
}

_LOADING_TEXTS = {
    "open_now": OPEN_NOW_LOADING_TEXT,
    "coffee": COFFEE_LOADING_TEXT,
    "food": FOOD_LOADING_TEXT,
    "walks": WALKS_LOADING_TEXT,
    "dog_friendly": DOG_FRIENDLY_LOADING_TEXT,
}

_EMPTY_TEMPLATES = {
    "open_now": place_texts.OPEN_NOW_EMPTY_TEMPLATE,
    "coffee": place_texts.COFFEE_EMPTY_TEMPLATE,
    "food": place_texts.FOOD_EMPTY_TEMPLATE,
    "walks": place_texts.WALKS_EMPTY_TEMPLATE,
    "dog_friendly": place_texts.DOG_FRIENDLY_EMPTY_TEMPLATE,
}

_HEADER_TEMPLATES = {
    "open_now": place_texts.OPEN_NOW_RESULT_HEADER_TEMPLATE,
    "coffee": place_texts.COFFEE_RESULT_HEADER_TEMPLATE,
    "food": place_texts.FOOD_RESULT_HEADER_TEMPLATE,
    "walks": place_texts.WALKS_RESULT_HEADER_TEMPLATE,
    "dog_friendly": place_texts.DOG_FRIENDLY_RESULT_HEADER_TEMPLATE,
}