from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from data.scripts.image_enrichment_rules import image_block

CATALOG = Path("frontend/public/data/zelenogradsk_places.json")


def enrich_catalog(path: Path = CATALOG, fetched_at: str | None = None) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    current = fetched_at or date.today().isoformat()
    items = tuple(map(lambda place: enrich_place(place, current), payload.get("items", [])))
    next_payload = {**payload, "schema_version": "1.3", "items": items}
    path.write_text(json.dumps(next_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return status_counts(items)


def enrich_place(place: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    image = image_block(place, fetched_at)
    return {**place, "image": image, "image_source": image["source"],
            "image_is_exact": image["match_status"] == "exact_place_photo"}


def status_counts(items: tuple[dict[str, Any], ...]) -> dict[str, int]:
    return dict(map(lambda status: (status, count_status(items, status)), statuses(items)))


def statuses(items: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return tuple(sorted({item["image"]["match_status"] for item in items}))


def count_status(items: tuple[dict[str, Any], ...], status: str) -> int:
    return sum(map(lambda item: int(item["image"]["match_status"] == status), items))


def main() -> None:
    print(json.dumps(enrich_catalog(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
