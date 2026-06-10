from telegram_bot.services.address_context import get_user_address
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.user_context import get_user_city


async def resolve_place_city_slug(
    user_id: int,
    client: RecommendationApiClient,
    city_query: str | None = None,
) -> str | None:
    if city_query is not None:
        city = await client.get_city_center_for_address(city_query)
        if city.get("matched") is True:
            slug = city.get("slug")
            return slug if isinstance(slug, str) and slug else get_user_city(user_id)

    selected = get_user_city(user_id)
    if selected is not None:
        return selected

    address = get_user_address(user_id)
    if address is None:
        return None

    city = await client.get_city_center_for_address(address["raw_address"])
    slug = city.get("slug")
    return slug if isinstance(slug, str) and slug else None
