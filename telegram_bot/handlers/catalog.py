from __future__ import annotations

import logging
from contextlib import suppress
from typing import Awaitable, Callable

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.orm import Session

from db.session import SessionLocal
from telegram_bot import renderers
from telegram_bot.analytics import log_event
from telegram_bot.callbacks import parse_callback
from telegram_bot.keyboards import catalog as kb
from telegram_bot.schemas import BotCity, BotPlace, BotRoute
from telegram_bot.services.facade import BotFacade
from telegram_bot.session import (
    get_or_create_session,
    pop_nav,
    push_nav,
    resolve_short_id,
    save_session,
    toggle_favorite,
)
from telegram_bot.utils import haversine_meters

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await _with_session(message, _start_flow)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await _with_session(message, _show_main_menu_message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(renderers.help_text(), reply_markup=kb.back_to_menu())


@router.message(F.location)
async def location_message(message: Message) -> None:
    async def action(db: Session, session, facade: BotFacade) -> None:
        if not message.location:
            await message.answer("Не удалось получить геолокацию.", reply_markup=kb.back_to_menu())
            return
        session.last_location = {
            "lat": message.location.latitude,
            "lng": message.location.longitude,
        }
        save_session(db, session)
        if not session.selected_city_slug:
            await _show_city_select_message(message, facade)
            return
        places = facade.nearby_places(session.selected_city_slug, message.location.latitude, message.location.longitude)
        log_event(db, session, "nearby_used", payload={"results_count": len(places)})
        page = type("PageLike", (), {"items": places, "page": 0, "has_next": False})()
        await message.answer(
            renderers.places_list_text("📍 Рядом с тобой", places, 0),
            reply_markup=kb.places_page(page, session, "near", "list", "all"),
        )

    await _with_session(message, action)


@router.message()
async def text_message(message: Message) -> None:
    text = (message.text or "").strip()
    async def action(db: Session, session, facade: BotFacade) -> None:
        if not text:
            await message.answer("Отправь текстовый запрос или выбери действие в меню.", reply_markup=kb.back_to_menu())
            return
        lowered = text.lower()
        if lowered in {"главное меню", "меню"}:
            await _show_main_menu_message(db, session, facade, message)
            return
        if lowered in {"помощь", "что умеет бот"}:
            await message.answer(renderers.help_text(), reply_markup=kb.back_to_menu())
            return
        if not session.selected_city_slug:
            await _show_city_select_message(message, facade)
            return
        page = facade.search_places(session.selected_city_slug, text)
        log_event(db, session, "search_query", payload={"query": text, "results_count": len(page.items)})
        if not page.items:
            log_event(db, session, "search_no_results", payload={"query": text})
            await message.answer(renderers.no_results_text(text), reply_markup=kb.back_to_menu())
            return
        await message.answer(
            renderers.places_list_text(f"🔎 Поиск: {text}", page.items, page.page),
            reply_markup=kb.places_page(page, session, "p", "src", text),
        )

    await _with_session(message, action)


@router.callback_query()
async def callback_handler(callback: CallbackQuery) -> None:
    if callback.message is None:
        await callback.answer()
        return
    async def action(db: Session, session, facade: BotFacade) -> None:
        data = str(callback.data or "")
        parsed = parse_callback(data)
        if data != "back":
            push_nav(session, data)
        try:
            await _dispatch_callback(callback, db, session, facade, parsed.scope, parsed.action, parsed.parts)
            save_session(db, session)
        except Exception:
            db.rollback()
            logger.exception("Telegram callback failed")
            await _edit_or_answer(callback, renderers.error_text(), reply_markup=kb.back_to_menu())
        finally:
            with suppress(Exception):
                await callback.answer()

    await _with_callback_session(callback, action)


async def _dispatch_callback(callback: CallbackQuery, db: Session, session, facade: BotFacade, scope: str, action: str | None, parts: tuple[str, ...]) -> None:
    if scope == "m" and action == "main":
        await _show_main_menu_callback(callback, session, facade)
        return
    if scope == "c":
        await _handle_city(callback, db, session, facade, action, parts)
        return
    if scope == "r":
        await _handle_route(callback, db, session, facade, action, parts)
        return
    if scope == "rn":
        await _handle_route_navigation(callback, db, session, facade, action, parts)
        return
    if scope == "p":
        await _handle_place(callback, db, session, facade, action, parts)
        return
    if scope == "near":
        await _handle_nearby(callback, session, facade, action, parts)
        return
    if scope == "open":
        await _handle_open_now(callback, db, session, facade, parts)
        return
    if scope == "fav":
        await _handle_favorites(callback, db, session, facade, action, parts)
        return
    if scope == "help":
        await _edit_or_answer(callback, renderers.help_text(), reply_markup=kb.back_to_menu())
        return
    if scope == "back":
        await _handle_back(callback, db, session, facade)
        return
    await _edit_or_answer(callback, renderers.error_text(), reply_markup=kb.back_to_menu())


async def _start_flow(db: Session, session, facade: BotFacade, message: Message) -> None:
    cities = facade.published_cities()
    log_event(db, session, "bot_started")
    if len(cities) == 1:
        session.selected_city_slug = cities[0].slug
        save_session(db, session)
        await message.answer(renderers.main_menu_text(cities[0]), reply_markup=kb.main_menu())
        return
    await message.answer(renderers.start_text())
    await message.answer(renderers.city_select_text(cities), reply_markup=kb.city_list(cities))


async def _show_main_menu_message(db: Session, session, facade: BotFacade, message: Message) -> None:
    city = facade.city(session.selected_city_slug)
    if city is None:
        await _show_city_select_message(message, facade)
        return
    await message.answer(renderers.main_menu_text(city), reply_markup=kb.main_menu())


async def _show_main_menu_callback(callback: CallbackQuery, session, facade: BotFacade) -> None:
    city = facade.city(session.selected_city_slug)
    if city is None:
        await _show_city_select_callback(callback, facade)
        return
    await _edit_or_answer(callback, renderers.main_menu_text(city), reply_markup=kb.main_menu())


async def _show_city_select_message(message: Message, facade: BotFacade) -> None:
    cities = facade.published_cities()
    await message.answer(renderers.city_select_text(cities), reply_markup=kb.city_list(cities))


async def _show_city_select_callback(callback: CallbackQuery, facade: BotFacade) -> None:
    cities = facade.published_cities()
    await _edit_or_answer(callback, renderers.city_select_text(cities), reply_markup=kb.city_list(cities))


async def _handle_city(callback: CallbackQuery, db: Session, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    if action == "list":
        await _show_city_select_callback(callback, facade)
        return
    if action == "set" and parts:
        city = facade.city(parts[0])
        if city is None:
            await _show_city_select_callback(callback, facade)
            return
        session.selected_city_slug = city.slug
        session.current_flow = "main"
        session.nav_stack = ["m:main"]
        save_session(db, session)
        log_event(db, session, "city_selected", entity_type="city", entity_id=city.slug)
        await _edit_or_answer(callback, renderers.main_menu_text(city), reply_markup=kb.main_menu())
        return
    await _show_city_select_callback(callback, facade)


async def _handle_route(callback: CallbackQuery, db: Session, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    city = facade.city(session.selected_city_slug)
    if city is None:
        await _show_city_select_callback(callback, facade)
        return
    if action == "list":
        page_no = _int(parts[0] if parts else "0")
        page = facade.routes(city.slug, page_no)
        await _edit_or_answer(callback, renderers.routes_list_text(city, page.items, page.page), reply_markup=kb.routes_page(page, session))
        return
    if action in {"view", "pts", "go"} and parts:
        route = _route_by_short_id(facade, session, parts[0])
        if route is None:
            await _edit_or_answer(callback, "Маршрут недоступен.", reply_markup=kb.back_to_menu())
            return
        if action == "pts":
            await _edit_or_answer(callback, renderers.route_points_text(route), reply_markup=kb.route_card(route, session))
            return
        if action == "go":
            session.route_session = {"route_id": route.id, "current_index": 0, "visited": [], "started_at": callback.message.date.isoformat() if callback.message else None}
            save_session(db, session)
            log_event(db, session, "route_started", entity_type="route", entity_id=route.id)
            await _render_route_step(callback, session, route, 0)
            return
        log_event(db, session, "route_viewed", entity_type="route", entity_id=route.id)
        await _edit_or_answer(callback, renderers.route_card_text(route), reply_markup=kb.route_card(route, session))
        return
    await _edit_or_answer(callback, renderers.error_text(), reply_markup=kb.back_to_menu())


async def _handle_route_navigation(callback: CallbackQuery, db: Session, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    route_state = session.route_session if isinstance(session.route_session, dict) else None
    if not route_state:
        await _edit_or_answer(callback, "Активный маршрут не найден.", reply_markup=kb.back_to_menu())
        return
    route = facade.route(int(route_state.get("route_id", 0)))
    if route is None:
        session.route_session = None
        await _edit_or_answer(callback, "Маршрут больше недоступен.", reply_markup=kb.back_to_menu())
        return
    if action == "done":
        visited = list(route_state.get("visited", []))
        log_event(db, session, "route_completed", entity_type="route", entity_id=route.id, payload={"visited": len(visited), "total": len(route.points)})
        session.route_session = None
        save_session(db, session)
        await _edit_or_answer(callback, renderers.route_completed_text(route, len(visited)), reply_markup=kb.back_to_menu())
        return
    index = _int(parts[0] if parts else route_state.get("current_index", 0))
    index = min(max(index, 0), len(route.points) - 1)
    visited = list(route_state.get("visited", []))
    if action == "visit" and index not in visited:
        visited.append(index)
        log_event(db, session, "route_point_visited", entity_type="route", entity_id=route.id, payload={"index": index})
        index = min(index + 1, len(route.points) - 1)
    route_state["visited"] = visited
    route_state["current_index"] = index
    session.route_session = route_state
    save_session(db, session)
    if len(visited) >= len(route.points):
        session.route_session = None
        save_session(db, session)
        await _edit_or_answer(callback, renderers.route_completed_text(route, len(visited)), reply_markup=kb.back_to_menu())
        return
    await _render_route_step(callback, session, route, index)


async def _handle_place(callback: CallbackQuery, db: Session, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    if not session.selected_city_slug:
        await _show_city_select_callback(callback, facade)
        return
    if action == "cat" and len(parts) >= 2:
        category = parts[0]
        page_no = _int(parts[1])
        page = facade.places_by_category(session.selected_city_slug, category, page_no)
        title = "☕ Еда и кофе" if category == "food" else "👀 Что посмотреть"
        await _edit_or_answer(callback, renderers.places_list_text(title, page.items, page.page), reply_markup=kb.places_page(page, session, "p", "cat", category))
        return
    if action == "src" and len(parts) >= 2:
        query = parts[0]
        page_no = _int(parts[1])
        page = facade.search_places(session.selected_city_slug, query, page_no)
        await _edit_or_answer(callback, renderers.places_list_text(f"🔎 Поиск: {query}", page.items, page.page), reply_markup=kb.places_page(page, session, "p", "src", query))
        return
    if action == "view" and parts:
        place_id = resolve_short_id(session, parts[0])
        place = facade.place(place_id or 0)
        if place is None:
            await _edit_or_answer(callback, "Место недоступно.", reply_markup=kb.back_to_menu())
            return
        log_event(db, session, "place_viewed", entity_type="place", entity_id=place.id)
        await _send_place_card(callback, session, place)
        return
    await _edit_or_answer(callback, renderers.error_text(), reply_markup=kb.back_to_menu())


async def _handle_nearby(callback: CallbackQuery, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    if action == "ask" or not session.last_location:
        await callback.message.answer(renderers.nearby_request_text(), reply_markup=kb.request_location()) if callback.message else None
        return
    if not session.selected_city_slug:
        await _show_city_select_callback(callback, facade)
        return
    location = session.last_location
    places = facade.nearby_places(session.selected_city_slug, float(location["lat"]), float(location["lng"]), parts[0] if parts else None)
    page = type("PageLike", (), {"items": places, "page": 0, "has_next": False})()
    await _edit_or_answer(callback, renderers.places_list_text("📍 Рядом с тобой", places, 0), reply_markup=kb.places_page(page, session, "near", "list", "all"))


async def _handle_open_now(callback: CallbackQuery, db: Session, session, facade: BotFacade, parts: tuple[str, ...]) -> None:
    if not session.selected_city_slug:
        await _show_city_select_callback(callback, facade)
        return
    page_no = _int(parts[0] if parts else "0")
    page = facade.open_now(session.selected_city_slug, page_no)
    log_event(db, session, "open_now_used", payload={"results_count": len(page.items)})
    if not page.items:
        await _edit_or_answer(callback, renderers.open_now_empty_text(), reply_markup=kb.back_to_menu())
        return
    await _edit_or_answer(callback, renderers.places_list_text("🕐 Открыто сейчас", page.items, page.page), reply_markup=kb.places_page(page, session, "open", "list"))


async def _handle_favorites(callback: CallbackQuery, db: Session, session, facade: BotFacade, action: str | None, parts: tuple[str, ...]) -> None:
    if action == "toggle" and len(parts) >= 2:
        entity_id = resolve_short_id(session, parts[1])
        if entity_id is not None:
            added = toggle_favorite(session, parts[0], entity_id)
            save_session(db, session)
            log_event(db, session, "favorite_added" if added else "favorite_removed", entity_type="route" if parts[0] == "r" else "place", entity_id=entity_id)
        await callback.answer("Сохранено" if entity_id is not None else "Недоступно")
        return
    favorites = {"places": [], "routes": [], **(session.favorites or {})}
    routes = facade.favorite_routes(favorites.get("routes", []))
    places = facade.favorite_places(favorites.get("places", []))
    lines = ["<b>❤️ Избранное</b>", ""]
    if routes:
        lines.append("Маршруты:")
        lines.extend(f"• {route.title}" for route in routes)
        lines.append("")
    if places:
        lines.append("Места:")
        lines.extend(f"• {place.title}" for place in places)
    if not routes and not places:
        lines.append("Пока пусто. Сохраняй места и маршруты кнопкой ❤️.")
    await _edit_or_answer(callback, "\n".join(lines), reply_markup=kb.back_to_menu())


async def _handle_back(callback: CallbackQuery, db: Session, session, facade: BotFacade) -> None:
    previous = pop_nav(session)
    save_session(db, session)
    if previous is None:
        await _show_main_menu_callback(callback, session, facade)
        return
    parsed = parse_callback(previous)
    await _dispatch_callback(callback, db, session, facade, parsed.scope, parsed.action, parsed.parts)


async def _render_route_step(callback: CallbackQuery, session, route: BotRoute, index: int) -> None:
    point = route.points[index]
    visited = list((session.route_session or {}).get("visited", [])) if isinstance(session.route_session, dict) else []
    distance = None
    if session.last_location and point.lat is not None and point.lng is not None:
        distance = haversine_meters(float(session.last_location["lat"]), float(session.last_location["lng"]), point.lat, point.lng)
    await _edit_or_answer(callback, renderers.route_step_text(route, point, len(visited), distance), reply_markup=kb.route_step(index, len(route.points), index in visited))


async def _send_place_card(callback: CallbackQuery, session, place: BotPlace) -> None:
    markup = kb.place_card(place, session)
    if callback.message is None:
        return
    if place.image_url:
        try:
            await callback.message.answer_photo(place.image_url, caption=renderers.place_card_text(place), reply_markup=markup)
            return
        except Exception:
            logger.exception("Failed to send Telegram place photo")
    await _edit_or_answer(callback, renderers.place_card_text(place), reply_markup=markup)


def _route_by_short_id(facade: BotFacade, session, short_id: str) -> BotRoute | None:
    route_id = resolve_short_id(session, short_id)
    return facade.route(route_id or 0)


async def _edit_or_answer(callback: CallbackQuery, text: str, *, reply_markup=None) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await callback.message.answer(text, reply_markup=reply_markup)


async def _with_session(message: Message, action: Callable[[Session, object, BotFacade, Message], Awaitable[None]]) -> None:
    if message.from_user is None:
        await message.answer(renderers.error_text(), reply_markup=kb.back_to_menu())
        return
    with SessionLocal() as db:
        session = get_or_create_session(db, message.from_user.id, message.from_user.username)
        facade = BotFacade(db)
        try:
            await action(db, session, facade, message)
            save_session(db, session)
        except Exception:
            db.rollback()
            logger.exception("Telegram message handler failed")
            await message.answer(renderers.error_text(), reply_markup=kb.back_to_menu())


async def _with_callback_session(callback: CallbackQuery, action: Callable[[Session, object, BotFacade], Awaitable[None]]) -> None:
    with SessionLocal() as db:
        session = get_or_create_session(db, callback.from_user.id, callback.from_user.username)
        facade = BotFacade(db)
        await action(db, session, facade)


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
