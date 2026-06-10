from telegram_bot.services.context_store import database, memory
from telegram_bot.services.context_store.types import (
    ContextSnapshot,
    UserAddress,
    UserLocation,
)


def save_user_location(user_id: int, lat: float, lng: float) -> None:
    memory.save_location(user_id, lat, lng)
    database.save_location(user_id, lat, lng)


def get_user_location(user_id: int) -> UserLocation | None:
    stored = database.get_location(user_id)
    if stored is not None:
        memory.save_location(user_id, stored["lat"], stored["lng"])
        return stored
    return memory.get_location(user_id)


def save_user_address(user_id: int, raw_address: str) -> None:
    memory.save_address(user_id, raw_address)
    database.save_address(user_id, raw_address)


def get_user_address(user_id: int) -> UserAddress | None:
    stored = database.get_address(user_id)
    if stored is not None:
        memory.save_address(user_id, stored["raw_address"])
        return stored
    return memory.get_address(user_id)


def save_user_route(user_id: int, route: dict[str, object]) -> None:
    memory.save_route(user_id, route)
    database.save_route(user_id, route)


def get_user_route(user_id: int) -> dict[str, object] | None:
    stored = database.get_route(user_id)
    if stored is not None:
        memory.save_route(user_id, stored)
        return stored
    return memory.get_route(user_id)


def save_user_city(user_id: int, slug: str) -> None:
    memory.save_city(user_id, slug)
    database.save_city(user_id, slug)


def get_user_city(user_id: int) -> str | None:
    stored = database.get_city(user_id)
    if stored is not None:
        memory.save_city(user_id, stored["slug"])
        return stored["slug"]
    cached = memory.get_city(user_id)
    return cached["slug"] if cached is not None else None


def get_user_context_snapshot(user_id: int) -> ContextSnapshot:
    location = get_user_location(user_id)
    address = get_user_address(user_id)
    route = get_user_route(user_id)
    return {
        "has_location": location is not None,
        "raw_address": address["raw_address"] if address is not None else None,
        "has_route": route is not None,
        "route_points": _route_points_count(route),
        "selected_city_slug": get_user_city(user_id),
    }


def reset_user_context(user_id: int) -> None:
    memory.reset_context(user_id)
    database.reset_context(user_id)


def _route_points_count(route: dict[str, object] | None) -> int:
    raw = route.get("points") if route is not None else None
    return len(raw) if isinstance(raw, list) else 0
