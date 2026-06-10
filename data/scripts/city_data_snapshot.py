"""Снимок качества данных города (до/после pipeline)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.place import Place
from services.city_readiness.score import compute_city_readiness
from services.city_slug_resolver import resolve_city_by_slug
from services.route_eligibility import route_eligible_sql_conditions


def snapshot(city_slug: str) -> dict[str, object]:
    with SessionLocal() as db:
        city = resolve_city_by_slug(db, city_slug)
        if city is None:
            raise SystemExit(f"Город не найден: {city_slug}")
        base = db.query(Place).filter(Place.city_id == city.id)
        total = base.count()
        readiness = compute_city_readiness(db, city_slug=city.slug) or {}
        return {
            "city_slug": city.slug,
            "places_total": total,
            "with_address": base.filter(Place.address.isnot(None), Place.address != "").count(),
            "without_address": base.filter((Place.address.is_(None)) | (Place.address == "")).count(),
            "with_photo": base.filter(Place.image_url.isnot(None)).count(),
            "without_photo": base.filter(Place.image_url.is_(None)).count(),
            "with_description": base.filter(Place.short_description.isnot(None), Place.short_description != "").count(),
            "published": base.filter(Place.is_published.is_(True)).count(),
            "route_eligible": base.filter(*route_eligible_sql_conditions()).count(),
            "readiness": readiness,
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--city", required=True)
    args = p.parse_args()
    print(json.dumps(snapshot(args.city), ensure_ascii=False, indent=2, default=str))
