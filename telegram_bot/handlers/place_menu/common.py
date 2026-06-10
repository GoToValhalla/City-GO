import logging
from collections.abc import Mapping, Sequence
from typing import cast

from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.backend_errors import friendly_backend_error
from telegram_bot.services.messages import BACKEND_ERROR_TEMPLATE
from telegram_bot.services.place_messages import PLACE_CARD_PHOTO_UNAVAILABLE, RESULT_ITEM_TEMPLATE

logger = logging.getLogger(__name__)

ApiResult = Mapping[str, object]
PlaceItem = Mapping[str, object]


def result_ok(result: ApiResult) -> bool:
    return result.get("ok") is True


def result_text(result: ApiResult, key: str, fallback: str = "") -> str:
    value = result.get(key)
    return value if isinstance(value, str) else fallback


def result_items(result: ApiResult) -> list[PlaceItem]:
    items = result.get("items")
    return cast(list[PlaceItem], items) if isinstance(items, list) else []


def _clean_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def extract_title(item: PlaceItem) -> str:
    title = (
        _clean_text(item.get("title"))
        or _clean_text(item.get("name"))
        or _clean_text(item.get("place_name"))
    )
    return title or f"Place #{item.get('id', 'unknown')}"


def build_result_lines(header: str, items: Sequence[PlaceItem]) -> list[str]:
    item_lines = map(
        lambda item: RESULT_ITEM_TEMPLATE.format(title=extract_title(item)),
        items[:10],
    )
    return [header, *item_lines]


async def answer_backend_error(message: Message, result: ApiResult) -> None:
    await message.answer(
        BACKEND_ERROR_TEMPLATE.format(
            base_url=result_text(result, "base_url"),
            error=friendly_backend_error(result.get("error")),
        ),
        reply_markup=get_main_menu_keyboard(),
    )


async def answer_loading(message: Message, text: str) -> None:
    await message.answer(text, reply_markup=get_main_menu_keyboard())


def build_place_card_caption(item: PlaceItem) -> str:
    title = extract_title(item)
    lines = [f"<b>{title}</b>"]

    description = _clean_text(item.get("short_description"))
    if description:
        lines.append(description)

    address = _clean_text(item.get("address"))
    if address:
        lines.append(f"📍 {address}")

    image_url = _clean_text(item.get("image_url"))
    if not image_url:
        lines.append(PLACE_CARD_PHOTO_UNAVAILABLE)

    return "\n\n".join(lines)


async def send_place_card(message: Message, item: PlaceItem) -> None:
    caption = build_place_card_caption(item)
    image_url = _clean_text(item.get("image_url"))
    keyboard = get_main_menu_keyboard()

    if image_url:
        try:
            await message.answer_photo(photo=image_url, caption=caption, reply_markup=keyboard)
            return
        except Exception:
            logger.exception("Telegram photo send failed for place card")

    await message.answer(caption, reply_markup=keyboard)


async def answer_city_result(
    message: Message,
    result: ApiResult,
    empty_template: str,
    header_template: str,
    city_slug: str | None = None,
) -> None:
    display_slug = city_slug or "выбранный город"

    if not result_ok(result):
        await answer_backend_error(message, result)
        return

    items = result_items(result)

    if not items:
        await message.answer(
            empty_template.format(city_slug=display_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await message.answer(
        header_template.format(city_slug=display_slug),
        reply_markup=get_main_menu_keyboard(),
    )

    for item in items[:10]:
        await send_place_card(message, item)