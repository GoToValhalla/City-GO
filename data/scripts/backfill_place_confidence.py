"""Backfill initial place existence confidence from already imported source fields."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.place import Place
from services.place_verification_mutation import transition_place_verification
from services.place_verification_service import confidence_level


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill place existence confidence.")
    parser.add_argument("--city", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def initial_score(place: Place) -> int:
    title_ok = bool((place.title or "").strip())
    coords_ok = place.lat is not None and place.lng is not None
    address_ok = bool((place.address or "").strip()) and place.address != "Адрес не указан"
    source_ok = bool((place.source_url or "").strip())

    if not title_ok:
        return 10
    if title_ok and coords_ok and address_ok and source_ok:
        return 75
    if title_ok and coords_ok and source_ok:
        return 65
    if title_ok and coords_ok:
        return 45
    return 30


def run() -> dict[str, object]:
    args = parse_args()
    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == args.city).first()
        if city is None:
            raise SystemExit(f"City not found: {args.city}")

        places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
        updated = 0
        preview = []

        for place in places:
            if (place.verification_status or "unverified") == "verified":
                continue

            score = initial_score(place)
            level = confidence_level(score)
            status = "unverified"

            preview.append(
                {
                    "place_id": place.id,
                    "title": place.title,
                    "score": score,
                    "level": level,
                    "verification_status": status,
                }
            )

            if args.apply:
                transition_place_verification(
                    db,
                    place,
                    to_status=status,
                    actor="backfill_place_confidence_script",
                    confidence_score=score,
                    confidence_level=level,
                    verification_source=place.source or "system_inference",
                    verification_method="import_inferred",
                )
                updated += 1

        if args.apply:
            db.commit()

        return {"city_slug": args.city, "places": len(places), "updated": updated, "dry_run": args.dry_run, "preview": preview[:20]}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
