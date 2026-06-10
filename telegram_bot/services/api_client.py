from core.config import settings
from telegram_bot.services.citygo_api_requests import ApiResult, fetch_health, fetch_items, post_json


class CityGoApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.backend_base_url).rstrip("/")

    async def get_health(self) -> ApiResult:
        return await fetch_health(self.base_url)

    async def get_available_cities(self, include_draft: bool = False) -> ApiResult:
        return await fetch_items(
            self.base_url,
            "/cities/available",
            {"include_draft": include_draft},
        )

    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
    ) -> ApiResult:
        return await fetch_items(
            self.base_url,
            "/nearby/",
            {"lat": lat, "lng": lng, "radius_km": radius_km},
        )

    async def get_open_now_places(self, city_slug: str) -> ApiResult:
        return await fetch_items(self.base_url, "/open-now/", {"city_slug": city_slug})

    async def get_places(
        self,
        city_slug: str | None = None,
        category_id: int | None = None,
        tag_id: int | None = None,
    ) -> ApiResult:
        params: dict[str, object] = {}
        if city_slug is not None:
            params["city_slug"] = city_slug
        if category_id is not None:
            params["category_id"] = category_id
        if tag_id is not None:
            params["tag_id"] = tag_id
        return await fetch_items(self.base_url, "/places/", params)

    async def get_coffee_places(self, city_slug: str | None = None) -> ApiResult:
        return await self.get_places(
            city_slug=_city_or_default(city_slug),
            category_id=settings.coffee_category_id,
            tag_id=settings.coffee_tag_id,
        )

    async def get_food_places(self, city_slug: str | None = None) -> ApiResult:
        return await self.get_places(
            city_slug=_city_or_default(city_slug),
            category_id=settings.food_category_id,
            tag_id=settings.food_tag_id,
        )

    async def get_walk_places(self, city_slug: str | None = None) -> ApiResult:
        return await self.get_places(
            city_slug=_city_or_default(city_slug),
            category_id=settings.walks_category_id,
            tag_id=settings.walks_tag_id,
        )

    async def get_dog_friendly_places(self, city_slug: str | None = None) -> ApiResult:
        return await self.get_places(
            city_slug=_city_or_default(city_slug),
            category_id=settings.dog_friendly_category_id,
            tag_id=settings.dog_friendly_tag_id,
        )

    async def create_discovery_request(
        self,
        city_slug: str,
        name: str,
        telegram_user_id: int | None,
    ) -> ApiResult:
        return await post_json(self.base_url, "/place-discovery/", {
            "city_slug": city_slug,
            "name": name,
            "source_type": "telegram_message",
            "submitted_by_telegram_user_id": telegram_user_id,
        })


def _city_or_default(city_slug: str | None) -> str:
    return city_slug or ""
