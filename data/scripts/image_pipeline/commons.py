from __future__ import annotations

from typing import Any

from data.scripts.image_pipeline.http_client import get_json

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def depicts_params(qid: str) -> dict[str, str]:
    return {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": f"haswbstatement:P180={qid}",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "format": "json",
    }


def fetch_depicts_images(qid: str) -> tuple[dict[str, Any], ...]:
    data = get_json(COMMONS_API, depicts_params(qid))
    pages = data.get("query", {}).get("pages", {})
    return tuple(filter(None, map(page_image, pages.values())))


def page_image(page: dict[str, Any]) -> dict[str, Any] | None:
    infos = page.get("imageinfo") or []
    if not infos:
        return None
    info = infos[0]
    meta = info.get("extmetadata", {})
    return {
        "url": info.get("url"),
        "source_url": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
        "license": meta_value(meta, "LicenseShortName"),
        "attribution": meta_value(meta, "Artist") or "Wikimedia Commons contributors",
    }


def meta_value(meta: dict[str, Any], key: str) -> str | None:
    value = meta.get(key, {})
    return value.get("value") if isinstance(value, dict) else None
