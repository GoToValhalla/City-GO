from __future__ import annotations

from typing import cast

import httpx

from telegram_bot.services.backend_request_log import (
    log_backend_error,
    log_backend_success,
    request_started,
)


async def fetch_place_titles(base_url: str, place_ids: list[str]) -> dict[str, str]:
    unique_ids = list(dict.fromkeys(place_ids))
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        pairs = [
            await _fetch_place_title(client, base_url, place_id)
            for place_id in unique_ids
        ]
    return {place_id: title for place_id, title in pairs if title}


async def _fetch_place_title(
    client: httpx.AsyncClient,
    base_url: str,
    place_id: str,
) -> tuple[str, str | None]:
    started = request_started()
    try:
        response = await client.get(f"{base_url}/places/{place_id}")
        response.raise_for_status()
        log_backend_success("places.title", base_url, started, response.status_code)
        data = cast(dict[str, object], response.json())
        title = data.get("title")
        return place_id, title if isinstance(title, str) else None
    except Exception as exc:
        log_backend_error("places.title", base_url, started, exc)
        return place_id, None
