from __future__ import annotations

import httpx

from core.config import settings
from telegram_bot.services.backend_request_log import (
    log_backend_error,
    log_backend_success,
    request_started,
)
from telegram_bot.services.city_center_client import (
    fetch_city_center_by_slug,
    fetch_city_center_for_text,
)
from telegram_bot.services.place_titles_client import fetch_place_titles


class RecommendationApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.backend_base_url).rstrip("/")

    async def build_route(
        self,
        lat: float,
        lng: float,
        minutes: int = 120,
        interests: tuple[str, ...] = (),
        avoided_categories: tuple[str, ...] = (),
        excluded_place_ids: tuple[str, ...] = (),
        city_slug: str | None = None,
        start_source: str = "city_center",
    ) -> dict[str, object]:
        url = f"{self.base_url}/v1/user-routes/build"
        payload = {
            "lat": lat,
            "lng": lng,
            "start_source": start_source,
            "start": {
                "type": start_source,
                "lat": lat,
                "lng": lng,
            },
            "time_budget_minutes": minutes,
            "interests": list(interests),
            "avoided_categories": list(avoided_categories),
            "excluded_place_ids": list(excluded_place_ids),
            "city_id": city_slug,
        }
        started = request_started()
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            log_backend_success("user_routes.build", self.base_url, started, response.status_code)
            return {"ok": True, "base_url": self.base_url, "data": response.json()}
        except Exception as exc:
            log_backend_error("user_routes.build", self.base_url, started, exc)
            return {"ok": False, "base_url": self.base_url, "error": str(exc)}

    async def correct_route(
        self,
        current_route: dict[str, object],
        action: str,
        **kwargs: object,
    ) -> dict[str, object]:
        url = f"{self.base_url}/v1/user-routes/correct"
        payload = {"current_route": current_route, "action": action, **kwargs}
        started = request_started()
        try:
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
            log_backend_success("user_routes.correct", self.base_url, started, response.status_code)
            return {"ok": True, "base_url": self.base_url, "data": response.json()}
        except Exception as exc:
            log_backend_error("user_routes.correct", self.base_url, started, exc)
            return {"ok": False, "base_url": self.base_url, "error": str(exc)}

    async def get_place_titles(self, place_ids: list[str]) -> dict[str, str]:
        return await fetch_place_titles(self.base_url, place_ids)

    async def get_default_city_center(self) -> dict[str, object]:
        return await fetch_city_center_by_slug(
            self.base_url,
            settings.default_city_slug,
        )

    async def get_city_center_by_slug(self, city_slug: str) -> dict[str, object]:
        return await fetch_city_center_by_slug(self.base_url, city_slug)

    async def get_city_center_for_address(self, raw_address: str) -> dict[str, object]:
        return await fetch_city_center_for_text(
            self.base_url,
            raw_address,
        )
