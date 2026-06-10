from telegram_bot.services.route_start_types import RouteStart


def route_start_from_city(
    city: dict[str, object],
    source: str,
    label: str,
) -> RouteStart | None:
    if not city.get("ok"):
        return None
    return RouteStart(
        lat=float(city["lat"]),
        lng=float(city["lng"]),
        source=source,
        label=label,
    )


def address_label(raw_address: str, city: dict[str, object]) -> str:
    name = city.get("name")
    if city.get("matched") and isinstance(name, str):
        return f"адреса «{raw_address}», город {name} (приблизительно)"
    return f"адреса «{raw_address}» (приблизительно)"


def query_city_label(city: dict[str, object]) -> str:
    name = city.get("name")
    return f"города {name}" if isinstance(name, str) else "города из запроса"
