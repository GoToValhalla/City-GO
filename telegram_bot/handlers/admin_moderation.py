from __future__ import annotations

import logging
from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from db.session import SessionLocal
from services.admin_mobile_place_review import defer_place, list_review_cities, next_review_place, publish_place, rejected_places, reject_place, restore_place
from services.feature_toggle_service import is_toggle_enabled

logger = logging.getLogger(__name__)
router = Router()
CALLBACK_PREFIX = "admrev"
MAX_MESSAGE_TEXT = 3900
MAX_PHOTO_CAPTION = 950


@router.message(Command("moderation", "mod", "review"))
async def cmd_moderation(message: Message) -> None:
    await _remove_reply_keyboard(message)
    with SessionLocal() as db:
        if not _is_enabled(db):
            await message.answer("Модерация временно выключена.", reply_markup=ReplyKeyboardRemove())
            return
        if not _is_admin_message(message):
            await message.answer("Модерация мест доступна только администратору.", reply_markup=ReplyKeyboardRemove())
            return
        await message.answer(_cities_text(db), reply_markup=_cities_keyboard(db))


@router.callback_query(F.data.startswith(f"{CALLBACK_PREFIX}:"))
async def moderation_callback(callback: CallbackQuery) -> None:
    if not _is_admin_callback(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return
    parts = str(callback.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    city_slug = parts[2] if len(parts) > 2 else settings.default_city_slug
    place_id = _int(parts[3]) if len(parts) > 3 else 0
    actor = f"tg:{callback.from_user.id if callback.from_user else 'unknown'}"
    try:
        with SessionLocal() as db:
            if not _is_enabled(db):
                await callback.answer("Модерация временно выключена", show_alert=True)
                return
            if action == "cities":
                await _ack(callback, "Обновляю города…")
                await _edit(callback, _cities_text(db), _cities_keyboard(db))
                return
            if action == "next":
                await _ack(callback, f"Открываю {city_slug}…")
                await _send_next(callback, db, city_slug)
                return
            if action == "rejected":
                await _ack(callback, "Открываю отклонённые…")
                await _edit(callback, _rejected_text(db, city_slug), _rejected_keyboard(db, city_slug))
                return
            if action in {"publish", "reject", "defer", "restore"} and place_id:
                await _apply_action(callback, db, action, city_slug, place_id, actor)
                return
        await callback.answer("Команда не распознана", show_alert=False)
    except HTTPException as exc:
        await _show_callback_error(callback, str(exc.detail))
    except Exception:
        logger.exception("Telegram moderation callback failed", extra={"callback_data": callback.data})
        await _show_callback_error(callback, "Ошибка модерации. Смотри backend logs.")


def _cities_text(db: Session) -> str:
    payload = list_review_cities(db)
    items = list(payload.get("items") or [])
    if not items:
        return "<b>Модерация мест</b>\n\nГородов с очередью пока нет."
    lines = ["<b>Модерация мест</b>", "", "Выбери город:"]
    for city in items[:30]:
        lines.append(f"• {escape(str(city.get('name') or city.get('slug')))}: на проверке {city.get('needs_review', 0)}, отклонено {city.get('rejected', 0)}")
    return "\n".join(lines)


def _cities_keyboard(db: Session) -> InlineKeyboardMarkup:
    payload = list_review_cities(db)
    rows = []
    for city in list(payload.get("items") or [])[:30]:
        slug = str(city.get("slug"))
        name = str(city.get("name") or slug)
        needs_review = int(city.get("needs_review") or 0)
        rejected = int(city.get("rejected") or 0)
        rows.append([InlineKeyboardButton(text=f"{name} · {needs_review}/{rejected}", callback_data=f"{CALLBACK_PREFIX}:next:{slug}")])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="Обновить", callback_data=f"{CALLBACK_PREFIX}:cities")]])


async def _send_next(callback: CallbackQuery, db: Session, city_slug: str) -> None:
    payload = next_review_place(db, city_slug)
    place = payload.get("place")
    if not place:
        await _edit(callback, f"<b>{escape(city_slug)}</b>\n\nОчередь пуста.", _empty_city_keyboard(city_slug))
        return
    await _send_place(callback, place, city_slug, int(payload.get("remaining") or 0))


async def _send_place(callback: CallbackQuery, place: dict[str, object], city_slug: str, remaining: int) -> None:
    text = _truncate(_place_text(place, city_slug, remaining), MAX_MESSAGE_TEXT)
    markup = _place_keyboard(city_slug, int(place.get("id") or 0))
    photo = _first_photo(place)
    if callback.message is None:
        return
    with suppress(Exception):
        await callback.message.edit_reply_markup(reply_markup=None)
    if photo:
        try:
            await callback.message.answer_photo(photo=photo, caption=_truncate(text, MAX_PHOTO_CAPTION), reply_markup=markup)
            return
        except Exception:
            logger.exception("Failed to send Telegram moderation photo", extra={"place_id": place.get("id"), "city_slug": city_slug})
    try:
        await callback.message.answer(text, reply_markup=markup)
    except Exception:
        logger.exception("Failed to send Telegram moderation place card", extra={"place_id": place.get("id"), "city_slug": city_slug})
        await _show_callback_error(callback, "Не удалось отправить карточку места. Смотри backend logs.")


async def _apply_action(callback: CallbackQuery, db: Session, action: str, city_slug: str, place_id: int, actor: str) -> None:
    if action == "publish":
        publish_place(db, place_id, actor)
        message = "Опубликовано"
    elif action == "reject":
        reject_place(db, place_id, actor)
        message = "Отклонено"
    elif action == "restore":
        restore_place(db, place_id, actor)
        message = "Возвращено в очередь"
    else:
        defer_place(db, place_id, actor)
        message = "Перенесено в конец очереди"
    await callback.answer(message, show_alert=False)
    await _send_next(callback, db, city_slug)


def _rejected_text(db: Session, city_slug: str) -> str:
    payload = rejected_places(db, city_slug)
    items = list(payload.get("items") or [])
    if not items:
        return f"<b>{escape(city_slug)}</b>\n\nОтклонённых мест нет."
    lines = [f"<b>{escape(city_slug)}</b>", "", "Отклонённые места:"]
    for place in items[:20]:
        lines.append(f"• #{place.get('id')} {escape(str(place.get('title') or 'Без названия'))}")
    return "\n".join(lines)


def _rejected_keyboard(db: Session, city_slug: str) -> InlineKeyboardMarkup:
    payload = rejected_places(db, city_slug)
    rows = []
    for place in list(payload.get("items") or [])[:20]:
        title = str(place.get("title") or "Без названия")[:32]
        rows.append([InlineKeyboardButton(text=f"↩️ {title}", callback_data=f"{CALLBACK_PREFIX}:restore:{city_slug}:{place.get('id')}")])
    rows.append([InlineKeyboardButton(text="⬅️ К очереди", callback_data=f"{CALLBACK_PREFIX}:next:{city_slug}"), InlineKeyboardButton(text="🏙 Города", callback_data=f"{CALLBACK_PREFIX}:cities")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _empty_city_keyboard(city_slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отклонённые", callback_data=f"{CALLBACK_PREFIX}:rejected:{city_slug}")],
        [InlineKeyboardButton(text="🏙 Города", callback_data=f"{CALLBACK_PREFIX}:cities")],
    ])


def _place_keyboard(city_slug: str, place_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"{CALLBACK_PREFIX}:publish:{city_slug}:{place_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"{CALLBACK_PREFIX}:reject:{city_slug}:{place_id}"), InlineKeyboardButton(text="⏭ В конец", callback_data=f"{CALLBACK_PREFIX}:defer:{city_slug}:{place_id}")],
        [InlineKeyboardButton(text="Отклонённые", callback_data=f"{CALLBACK_PREFIX}:rejected:{city_slug}"), InlineKeyboardButton(text="🏙 Города", callback_data=f"{CALLBACK_PREFIX}:cities")],
    ])


def _place_text(place: dict[str, object], city_slug: str, remaining: int) -> str:
    blockers = list(place.get("publication_blockers") or [])
    lines = [
        f"<b>{escape(str(place.get('title') or 'Без названия'))}</b>",
        f"Город: {escape(city_slug)} · осталось: {remaining}",
        f"Категория: {escape(str(place.get('category') or place.get('canonical_category') or 'не указана'))}",
        f"Адрес: {escape(str(place.get('address') or 'не указан'))}",
        "",
        escape(str(place.get("short_description") or "Описание не заполнено")),
    ]
    if blockers:
        lines.extend(["", "⚠️ Блокеры публикации:", *[f"• {escape(str(item))}" for item in blockers]])
    return "\n".join(lines)


def _first_photo(place: dict[str, object]) -> str | None:
    values = []
    for key in ("image_urls", "photo_urls"):
        raw = place.get(key)
        if isinstance(raw, list):
            values.extend(str(item) for item in raw if item)
    if place.get("image_url"):
        values.append(str(place["image_url"]))
    return values[0] if values else None


async def _edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    if callback.message is None:
        return
    limited_text = _truncate(text, MAX_MESSAGE_TEXT)
    with suppress(Exception):
        await callback.message.edit_text(limited_text, reply_markup=markup)
        return
    await callback.message.answer(limited_text, reply_markup=markup)


async def _remove_reply_keyboard(message: Message) -> None:
    with suppress(Exception):
        await message.answer("Клавиатура скрыта.", reply_markup=ReplyKeyboardRemove())


async def _ack(callback: CallbackQuery, text: str) -> None:
    with suppress(Exception):
        await callback.answer(text, show_alert=False)


async def _show_callback_error(callback: CallbackQuery, text: str) -> None:
    with suppress(Exception):
        await callback.answer(text, show_alert=True)
        return
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.answer(text)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + "…"


def _is_admin_message(message: Message) -> bool:
    user_id = message.from_user.id if message.from_user else None
    return _is_allowed(user_id, message.chat.id if message.chat else None)


def _is_admin_callback(callback: CallbackQuery) -> bool:
    user_id = callback.from_user.id if callback.from_user else None
    chat_id = callback.message.chat.id if callback.message else None
    return _is_allowed(user_id, chat_id)


def _is_allowed(user_id: int | None, chat_id: int | None) -> bool:
    allowed = _allowed_ids()
    return bool(allowed and ((user_id is not None and user_id in allowed) or (chat_id is not None and chat_id in allowed)))


def _allowed_ids() -> set[int]:
    raw = ",".join(value for value in (settings.telegram_admin_user_ids, settings.telegram_chat_id) if value)
    result: set[int] = set()
    for item in raw.replace(";", ",").split(","):
        with suppress(ValueError):
            result.add(int(item.strip()))
    return result


def _is_enabled(db: Session) -> bool:
    return is_toggle_enabled(db, "telegram_admin_moderation", default=False)


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
