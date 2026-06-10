from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.handlers.place_menu.common import answer_city_result, answer_loading
from telegram_bot.services import place_messages as place_texts
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.messages import (
    DOG_FRIENDLY_LOADING_TEXT,
    WALKS_LOADING_TEXT,
)
from telegram_bot.services.place_city_context import resolve_place_city_slug
from telegram_bot.services.recommendation_client import RecommendationApiClient

router = Router()


@router.message(F.text == "Куда погулять")
async def walks_handler(message: Message) -> None:
    await answer_loading(message, WALKS_LOADING_TEXT)
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_walk_places(city_slug)
    await answer_city_result(
        message,
        result,
        place_texts.WALKS_EMPTY_TEMPLATE,
        place_texts.WALKS_RESULT_HEADER_TEMPLATE,
        city_slug,
    )


@router.message(F.text == "С собакой")
async def dog_friendly_handler(message: Message) -> None:
    await answer_loading(message, DOG_FRIENDLY_LOADING_TEXT)
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_dog_friendly_places(city_slug)
    await answer_city_result(
        message,
        result,
        place_texts.DOG_FRIENDLY_EMPTY_TEMPLATE,
        place_texts.DOG_FRIENDLY_RESULT_HEADER_TEMPLATE,
        city_slug,
    )


async def _city_slug(message: Message) -> str | None:
    if message.from_user is None:
        return None
    return await resolve_place_city_slug(
        message.from_user.id,
        RecommendationApiClient(),
        message.text,
    )
