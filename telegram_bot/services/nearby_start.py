from telegram_bot.services.address_context import get_user_address
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.route_start_helpers import address_label, route_start_from_city
from telegram_bot.services.route_start_types import RouteStart
from telegram_bot.services.user_context import get_user_location


async def resolve_nearby_start(
    user_id: int,
    client: RecommendationApiClient,
    city_query: str | None = None,
) -> RouteStart | None:
    if city_query is not None:
        query_city = await client.get_city_center_for_address(city_query)
        if query_city.get("matched") is True:
            return route_start_from_city(
                query_city,
                source="text_city",
                label=address_label(city_query, query_city),
            )

    location = get_user_location(user_id)
    if location is not None:
        return RouteStart(
            lat=location["lat"],
            lng=location["lng"],
            source="user_location",
            label="вашей геолокации",
        )

    address = get_user_address(user_id)
    if address is None:
        return None

    city = await client.get_city_center_for_address(address["raw_address"])
    return route_start_from_city(
        city,
        source="manual_address",
        label=address_label(address["raw_address"], city),
    )
