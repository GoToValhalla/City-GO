from aiogram import F, Router
from aiogram.types import Message

from telegram_bot.handlers.city_selection import prompt_city
from telegram_bot.handlers.place_menu.common import (
    answer_city_result,
    answer_loading,
)
from telegram_bot.services import place_messages as place_texts
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.messages import (
    COFFEE_LOADING_TEXT,
    FOOD_LOADING_TEXT,
    OPEN_NOW_LOADING_TEXT,
)
from telegram_bot.services.place_city_context import resolve_place_city_slug
from telegram_bot.services.recommendation_client import RecommendationApiClient

router = Router()


@router.message(F.text == "Что открыто")
@router.message(F.text == "☕ Открыто сейчас")
async def open_now_handler(message: Message) -> None:
    await answer_loading(message, OPEN_NOW_LOADING_TEXT)
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_open_now_places(city_slug)
    await answer_city_result(
        message,
        result,
        place_texts.OPEN_NOW_EMPTY_TEMPLATE,
        place_texts.OPEN_NOW_RESULT_HEADER_TEMPLATE,
        city_slug,
    )


@router.message(F.text == "📍 Места")
async def places_handler(message: Message) -> None:
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_places(city_slug)
    await answer_city_result(
        message,
        result,
        "Пока нет опубликованных мест для города <b>{city_slug}</b>.",
        "Места в городе <b>{city_slug}</b>:",
        city_slug,
    )


@router.message(F.text == "🔎 Найти место")
async def find_place_hint_handler(message: Message) -> None:
    await message.answer("Напишите название или тип места, например: «где кофе» или «найди кафе у моря».")


@router.message(F.text == "Где кофе")
async def coffee_handler(message: Message) -> None:
    await answer_loading(message, COFFEE_LOADING_TEXT)
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_coffee_places(city_slug)
    await answer_city_result(
        message,
        result,
        place_texts.COFFEE_EMPTY_TEMPLATE,
        place_texts.COFFEE_RESULT_HEADER_TEMPLATE,
        city_slug,
    )


@router.message(F.text == "Где поесть")
async def food_handler(message: Message) -> None:
    await answer_loading(message, FOOD_LOADING_TEXT)
    city_slug = await _city_slug(message)
    if city_slug is None:
        await prompt_city(message)
        return
    result = await CityGoApiClient().get_food_places(city_slug)
    await answer_city_result(
        message,
        result,
        place_texts.FOOD_EMPTY_TEMPLATE,
        place_texts.FOOD_RESULT_HEADER_TEMPLATE,
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
