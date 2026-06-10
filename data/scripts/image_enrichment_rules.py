from __future__ import annotations

import re
from typing import Any

EXACT = re.compile("мурариум|водонапор|променад|набереж|парк|мост|кирх|вокзал|станц|кот", re.I)
CATEGORY_PHOTO = frozenset(("bar", "coffee", "food", "hotel", "service"))


def image_block(place: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    status = match_status(place)
    url = place.get("image_url")
    return {
        "url": url,
        "thumbnail_url": url,
        "source": source_for(status, url),
        "source_url": source_url(url),
        "license": "see source page" if url else None,
        "attribution": "Wikimedia Commons contributors" if url else "City Go placeholder",
        "match_status": status,
        "match_confidence": confidence_for(status),
        "depicts_qid": place.get("wikidata_id"),
        "last_fetched_at": fetched_at,
    }


def match_status(place: dict[str, Any]) -> str:
    if place.get("image_is_exact"):
        return "exact_place_photo"
    if EXACT.search(f"{place.get('slug', '')} {place.get('title', '')}"):
        return "exact_place_photo"
    return "category_photo" if place.get("category") in CATEGORY_PHOTO else "area_photo"


def confidence_for(status: str) -> str:
    return {"exact_place_photo": "high", "area_photo": "medium"}.get(status, "low")


def source_for(status: str, url: str | None) -> str:
    if status == "category_photo":
        return "internal_placeholder"
    return "wikimedia_commons" if url else "internal_placeholder"


def source_url(url: str | None) -> str | None:
    match = re.search(r"Special:FilePath/([^?]+)", url or "")
    return f"https://commons.wikimedia.org/wiki/File:{match.group(1)}" if match else url
