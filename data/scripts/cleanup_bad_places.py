"""Hide technical/non-tourist places that leaked into public catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.place import Place

BAD_TITLE_PATTERNS = (
    re.compile(r"\bгазпром\b", re.I),
    re.compile(r"\bgazprom\b", re.I),
    re.compile(r"\bлукойл\b", re.I),
    re.compile(r"\blukoil\b", re.I),
    re.compile(r"\bазс\b", re.I),
    re.compile(r"\bавтозаправ", re.I),
    re.compile(r"\bшиномонтаж\b", re.I),
    re.compile(r"\bавтомой", re.I),
)

BAD_CATEGORIES = {"fuel", "car_service", "parking", "atm", "bank"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hide bad imported places from public catalog.")
    parser.add_argument("--city", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def is_bad_place(place: Place) -> bool:
    title = place.title or ""
    category = place.category or ""
    if category in BAD_CATEGORIES:
        return True
    return any(pattern.search(title) for pattern in BAD_TITLE_PATTERNS)


def run() -> dict[str, object]:
    args = parse_args()
    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == args.city).first()
        if city is None:
            raise SystemExit(f"City not found: {args.city}")

        places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
        matched = [place for place in places if is_bad_place(place)]

        if args.apply:
            now = datetime.utcnow()
            for place in matched:
                place.is_active = False
                place.status = "hidden"
                place.verification_status = "not_public_catalog"
                place.verification_comment = "Hidden by cleanup_bad_places.py"
                place.updated_at = now
            db.commit()

        return {
            "city_slug": args.city,
            "scanned": len(places),
            "matched": len(matched),
            "updated": len(matched) if args.apply else 0,
            "dry_run": args.dry_run,
            "preview": [{"id": place.id, "title": place.title, "category": place.category} for place in matched[:50]],
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
