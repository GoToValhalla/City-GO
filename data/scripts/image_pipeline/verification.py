from __future__ import annotations

from typing import Any


def verification_queue(items: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return list(filter(None, map(queue_item, items)))


def queue_item(place: dict[str, Any]) -> dict[str, Any] | None:
    image = place.get("image") or {}
    status = image.get("match_status")
    confidence = image.get("match_confidence")
    if status == "exact_place_photo" and confidence == "high":
        return None
    return {
        "slug": place.get("slug"),
        "title": place.get("title"),
        "category": place.get("category"),
        "reason": reason(status, confidence),
        "image_url": image.get("url"),
        "image_status": status,
        "image_confidence": confidence,
    }


def reason(status: str | None, confidence: str | None) -> str:
    if status == "category_photo":
        return "needs exact or area photo"
    if status == "area_photo":
        return "area photo must not be treated as exact"
    if confidence == "low":
        return "low confidence image"
    return "needs editorial image review"
