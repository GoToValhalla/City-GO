from telegram_bot.services.recommendation_client import RecommendationApiClient

UNSUPPORTED_CITY_TEXT = (
    "<b>Пока этот город не поддерживается</b>\n\n"
    "Город может готовиться или ещё не опубликован. Выберите доступный город."
)


async def unsupported_city_message(
    client: RecommendationApiClient,
    city_query: str | None,
) -> str | None:
    if city_query is None:
        return None
    city = await client.get_city_center_for_address(city_query)
    published = city.get("launch_status", "published") == "published"
    return None if city.get("matched") is True and published else UNSUPPORTED_CITY_TEXT
