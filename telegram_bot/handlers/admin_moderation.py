from __future__ import annotations

from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from db.session import SessionLocal
from services.admin_mobile_place_review import defer_place, list_review_cities, next_review_place, publish_place, rejected_places, reject_place, restore_place

router = Router()
CALLBACK_PREFIX = "admrev"


@router.message(Command("moderation", "mod", "review"))
async def cmd_moderation(message: Message) -> None:
    if not _is_admin_message(message):
        await message.answer("Модерация мест доступна только администратору.")
        return
    with SessionLocal() as db:
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
            if action == "cities":
                await _edit(callback, _cities_text(db), _cities_keyboard(db))
                return
            if action == "next":
                await _send_next(callback, db, city_slug)
                return
            if action == "rejected":
                await _edit(callback, _rejected_text(db, city_slug), _rejected_keyboard(db, city_slug))
                return
            if action in {"publish", "reject", "defer", "restore"} and place_id:
                await _apply_action(callback, db, action, city_slug, place_id, actor)
                return
        await callback.answer("Команда не распознана", show_alert=False)
    except HTTPException as exc:
        await callback.answer(str(exc.detail), show_alert=True)
    except Exception:
        await callback.answer("Ошибка модерации. Смотри backend logs.", show_alert=True)
        raise


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
    text = _place_text(place, city_slug, remaining)
    markup = _place_keyboard(city_slug, int(place.get("id") or 0))
    photo = _first_photo(place)
    if callback.message is None:
        await callback.answer()
        return
    with suppress(Exception):
        await callback.message.edit_reply_markup(reply_markup=None)
    if photo:
        await callback.message.answer_photo(photo=photo, caption=text, reply_markup=markup)
    else:
        await callback.message.answer(text, reply_markup=markup)


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
        await callback.answer()
        return
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=markup)
        return
    await callback.message.answer(text, reply_markup=markup)


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


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
