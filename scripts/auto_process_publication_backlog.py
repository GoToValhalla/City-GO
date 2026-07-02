from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from db.session import SessionLocal
from models.city import City
from models.place import Place
from services.admin_mobile_place_review import is_trusted_auto_publish_candidate

AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")


def process_backlog(*, city_slug: str | None, limit: int) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    with SessionLocal() as db:
        query = db.query(Place).join(City, City.id == Place.city_id).filter(Place.publication_status.in_(AUTO_BACKLOG_STATUSES))
        if city_slug:
            query = query.filter(City.slug == city_slug)
        for place in query.order_by(Place.id.asc()).limit(limit).all():
            counters["checked"] += 1
            if is_trusted_auto_publish_candidate(place):
                counters["auto_publish_candidates"] += 1
            elif not place.address:
                counters["missing_address"] += 1
            elif not place.image_url:
                counters["missing_photo"] += 1
            elif place.is_duplicate_suspected:
                counters["duplicate_suspected"] += 1
            else:
                counters["left_auto_backlog"] += 1
    return dict(counters)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--city-slug")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-seconds", type=int)
    args = parser.parse_args()
    payload = process_backlog(city_slug=args.city_slug, limit=args.limit)
    payload["mode"] = "dry_run"
    payload["auto_rejected"] = 0
    payload["moved_to_manual_review"] = 0
    payload["failed"] = 0
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
