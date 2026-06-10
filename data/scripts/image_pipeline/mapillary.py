from __future__ import annotations

from typing import Any

from data.scripts.image_pipeline.http_client import get_json

MAPILLARY_API = "https://graph.mapillary.com/images"


def bbox(lat: float, lng: float, delta: float = 0.001) -> str:
    return f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"


def fetch_area_images(place: dict[str, Any], token: str | None) -> tuple[dict[str, Any], ...]:
    if not token or place.get("lat") is None or place.get("lng") is None:
        return ()
    params = {"access_token": token, "bbox": bbox(place["lat"], place["lng"]),
              "fields": "id,thumb_1024_url,captured_at", "limit": "5"}
    data = get_json(MAPILLARY_API, params)
    return tuple(map(area_image, data.get("data", ())))


def area_image(item: dict[str, Any]) -> dict[str, Any]:
    return {"url": item.get("thumb_1024_url"), "source_url": f"https://www.mapillary.com/app/?pKey={item.get('id')}",
            "source": "mapillary", "captured_at": item.get("captured_at")}
