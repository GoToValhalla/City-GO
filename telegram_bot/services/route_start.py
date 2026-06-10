from __future__ import annotations

from telegram_bot.services.address_context import get_user_address
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.route_start_helpers import (
    address_label,
    query_city_label,
    route_start_from_city,
)
from telegram_bot.services.route_start_types import RouteStart
from telegram_bot.services.user_context import get_user_location
from telegram_bot.services.user_context import get_user_city


async def resolve_route_start(
    user_id: int,
    client: RecommendationApiClient,
    city_query: str | None = None,
) -> RouteStart | None:
    query_start = await _query_city_start(client, city_query)
    if query_start is not None:
        return query_start

    location = get_user_location(user_id)
    if location is not None:
        return RouteStart(
            lat=location["lat"],
            lng=location["lng"],
            source="user_location",
            label="вашей геолокации",
        )

    address = get_user_address(user_id)
    if address is not None:
        return await _address_city_center_start(
            client,
            address["raw_address"],
        )

    selected_city = get_user_city(user_id)
    if selected_city is None:
        return None
    return await _city_center_start(
        client,
        selected_city,
        source="selected_city",
        label=f"центра города {selected_city}",
    )


async def _query_city_start(
    client: RecommendationApiClient,
    city_query: str | None,
) -> RouteStart | None:
    if city_query is None:
        return None
    city = await client.get_city_center_for_address(city_query)
    if city.get("matched") is not True:
        return None
    return route_start_from_city(
        city,
        source="text_city",
        label=query_city_label(city),
    )


async def _address_city_center_start(
    client: RecommendationApiClient,
    raw_address: str,
) -> RouteStart | None:
    city = await client.get_city_center_for_address(raw_address)
    return route_start_from_city(
        city,
        source="manual_address",
        label=address_label(raw_address, city),
    )


async def _city_center_start(
    client: RecommendationApiClient,
    city_slug: str,
    source: str,
    label: str,
) -> RouteStart | None:
    city = await client.get_city_center_by_slug(city_slug)
    return route_start_from_city(city, source, label)
