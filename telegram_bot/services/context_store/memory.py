from telegram_bot.services.context_store.types import SelectedCity, UserAddress, UserLocation

USER_LOCATIONS: dict[int, UserLocation] = {}
USER_ADDRESSES: dict[int, UserAddress] = {}
USER_ROUTES: dict[int, dict[str, object]] = {}
USER_CITIES: dict[int, SelectedCity] = {}


def save_location(user_id: int, lat: float, lng: float) -> None:
    USER_LOCATIONS[user_id] = {"lat": lat, "lng": lng}


def get_location(user_id: int) -> UserLocation | None:
    return USER_LOCATIONS.get(user_id)


def save_address(user_id: int, raw_address: str) -> None:
    USER_ADDRESSES[user_id] = {"raw_address": raw_address}


def get_address(user_id: int) -> UserAddress | None:
    return USER_ADDRESSES.get(user_id)


def save_route(user_id: int, route: dict[str, object]) -> None:
    USER_ROUTES[user_id] = route


def get_route(user_id: int) -> dict[str, object] | None:
    return USER_ROUTES.get(user_id)


def save_city(user_id: int, slug: str) -> None:
    USER_CITIES[user_id] = {"slug": slug}


def get_city(user_id: int) -> SelectedCity | None:
    return USER_CITIES.get(user_id)


def reset_context(user_id: int) -> None:
    USER_LOCATIONS.pop(user_id, None)
    USER_ADDRESSES.pop(user_id, None)
    USER_ROUTES.pop(user_id, None)
    USER_CITIES.pop(user_id, None)
