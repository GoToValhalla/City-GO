from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from telegram_bot.keyboards.city_selection import city_slug_from_callback
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.city_selection import (
    CITY_DRAFT_TEXT,
    CITY_REQUIRED_TEXT,
    available_city_items,
    city_by_slug,
    city_main_menu_text,
    city_selection_markup,
    main_menu_for_city,
)
from telegram_bot.services.user_context import save_user_city

router = Router()


@router.message(F.text == "⚙️ Сменить город")
@router.message(F.text == "Сменить город")
async def change_city_handler(message: Message) -> None:
    await prompt_city(message)


async def prompt_city(message: Message) -> None:
    await message.answer(CITY_REQUIRED_TEXT, reply_markup=await city_selection_markup())


@router.callback_query(F.data == "cities:all")
async def all_cities_callback(callback: CallbackQuery) -> None:
    cities = await available_city_items(CityGoApiClient(), include_draft=True)
    text = "\n".join(map(_city_line, cities)) or "Города пока не загружены."
    await callback.message.answer(text, reply_markup=await city_selection_markup()) if callback.message else None
    await callback.answer()


@router.callback_query(F.data.startswith("city:"))
async def city_callback(callback: CallbackQuery) -> None:
    slug = city_slug_from_callback(str(callback.data or ""))
    cities = await available_city_items(CityGoApiClient(), include_draft=True)
    city = city_by_slug(cities, slug or "")
    await _answer_city(callback, city)


async def _answer_city(callback: CallbackQuery, city: dict[str, object] | None) -> None:
    if callback.message is None:
        await callback.answer()
        return
    if city is None or city.get("launch_status") != "published":
        await callback.message.answer(CITY_DRAFT_TEXT, reply_markup=await city_selection_markup())
        await callback.answer()
        return
    save_user_city(callback.from_user.id, str(city["slug"]))
    await callback.message.answer(city_main_menu_text(city), reply_markup=main_menu_for_city())
    await callback.answer()


def _city_line(city: dict[str, object]) -> str:
    status = "доступен" if city.get("launch_status") == "published" else "готовится"
    return f"• {city.get('name', city.get('slug'))}: {status}"
