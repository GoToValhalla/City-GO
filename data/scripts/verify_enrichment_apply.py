"""Post-apply DB verification for place enrichment batches."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.place import Place
from services.place_enrichment_batch.paths import resolve_batch_paths

PREFIXES = ("Кафе:", "Еда:", "Культура:", "Музей:")
SEED = re.compile(r"Описание подготовлено по названию|требует проверки|seed", re.I)


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify enrichment apply in DB")
    p.add_argument("--city-slug", required=True)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--sample-size", type=int, default=5)
    return p.parse_args()


def _batch_ids(batch_id: str) -> list[int]:
    paths, _ = resolve_batch_paths(batch_id)
    rows = csv.DictReader(paths["enriched_csv"].read_text(encoding="utf-8").splitlines())
    return [int(r["id"]) for r in rows if r.get("id", "").strip().isdigit()]


def _prefix_count(text: str | None) -> bool:
    t = (text or "").strip()
    return any(t.startswith(p) for p in PREFIXES)


def main() -> None:
    args = _args()
    ids = _batch_ids(args.batch_id)
    db = SessionLocal()
    try:
        city = db.query(City).filter(City.slug == args.city_slug).first()
        if city is None:
            raise SystemExit(f"City not found: {args.city_slug}")
        places = (
            db.query(Place)
            .filter(Place.city_id == city.id, Place.id.in_(ids))
            .order_by(Place.id)
            .all()
        )
        tech = sum(1 for p in places if _prefix_count(p.short_description))
        seed = sum(1 for p in places if SEED.search(p.short_description or ""))
        sample = [
            {"title": p.title, "short_description": p.short_description, "address": p.address}
            for p in places[: args.sample_size]
        ]
        print(json.dumps({
            "city_slug": args.city_slug,
            "batch_id": args.batch_id,
            "batch_place_count": len(ids),
            "matched_places": len(places),
            "tech_prefixes_left": tech,
            "seed_text_left": seed,
            "sample": sample,
        }, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
