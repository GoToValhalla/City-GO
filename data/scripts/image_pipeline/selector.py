from __future__ import annotations

from datetime import date
from typing import Any

from data.scripts.image_enrichment_rules import image_block


def choose_image(
    place: dict[str, Any],
    candidates: dict[str, Any],
    fetched_at: str | None = None,
) -> dict[str, Any]:
    current = fetched_at or date.today().isoformat()
    for key, builder in (
        ("wikidata_p18", wikidata_image),
        ("commons_depicts", commons_image),
        ("official_og", official_image),
        ("mapillary_area", area_image),
    ):
        items = candidates.get(key) or ()
        if items:
            return builder(items[0], current)
    return image_block(place, current)


def wikidata_image(item: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    return exact(item.get("image"), "wikidata_p18", item.get("source_url"), fetched_at)


def commons_image(item: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    return {**exact(item.get("url"), "wikimedia_commons", item.get("source_url"), fetched_at),
            "license": item.get("license"), "attribution": item.get("attribution")}


def official_image(item: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    return {**exact(item.get("url"), "official_website", item.get("source_url"), fetched_at),
            "match_confidence": "medium"}


def area_image(item: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    return base(item.get("url"), "mapillary", item.get("source_url"), "area_photo", "medium", fetched_at)


def exact(url: str | None, source: str, source_url: str | None, fetched_at: str) -> dict[str, Any]:
    return base(url, source, source_url, "exact_place_photo", "high", fetched_at)


def base(url: str | None, source: str, source_url: str | None, status: str, confidence: str, fetched_at: str) -> dict[str, Any]:
    return {"url": url, "thumbnail_url": url, "source": source, "source_url": source_url,
            "license": "see source page", "attribution": None, "match_status": status,
            "match_confidence": confidence, "depicts_qid": None, "last_fetched_at": fetched_at}
