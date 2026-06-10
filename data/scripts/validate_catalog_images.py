from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG = Path("frontend/public/data/zelenogradsk_places.json")
STATUSES = frozenset(("exact_place_photo", "area_photo", "category_photo", "no_photo"))
CONFIDENCE = frozenset(("high", "medium", "low"))
SOURCES = frozenset(("wikimedia_commons", "wikidata_p18", "official_website",
                     "mapillary", "google_places", "internal_placeholder"))


def validate_catalog(path: Path = CATALOG) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return flatten(tuple(map(validate_place, payload.get("items", []))))


def validate_place(place: dict[str, Any]) -> tuple[str, ...]:
    image = place.get("image") or {}
    checks = (
        field_error(place, image, "match_status", STATUSES),
        field_error(place, image, "match_confidence", CONFIDENCE),
        field_error(place, image, "source", SOURCES),
        exact_without_url(place, image),
    )
    return tuple(filter(None, checks))


def field_error(place: dict[str, Any], image: dict[str, Any], field: str, allowed: frozenset[str]) -> str:
    value = image.get(field)
    return "" if value in allowed else f"{place.get('slug')}: invalid image.{field}={value}"


def exact_without_url(place: dict[str, Any], image: dict[str, Any]) -> str:
    if image.get("match_status") == "exact_place_photo" and not image.get("url"):
        return f"{place.get('slug')}: exact image requires url"
    return ""


def flatten(groups: tuple[tuple[str, ...], ...]) -> list[str]:
    return [item for group in groups for item in group]


def main() -> None:
    errors = validate_catalog()
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
