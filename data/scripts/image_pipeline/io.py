from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def catalog_items(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(payload.get("items", ()))


def raw_by_osm_url(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(map(lambda el: (osm_url(el), el), raw.get("elements", ())))


def osm_url(element: dict[str, Any]) -> str:
    return f"https://www.openstreetmap.org/{element.get('type')}/{element.get('id')}"


def raw_tags(place: dict[str, Any], raw_index: dict[str, dict[str, Any]]) -> dict[str, str]:
    return raw_index.get(place.get("source_url", ""), {}).get("tags", {}) or {}
