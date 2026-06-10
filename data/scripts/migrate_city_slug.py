"""Безопасная миграция slug города с сохранением алиаса."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from services.city_slug_resolver import resolve_city_by_slug


def run(argv: list[str] | None = None) -> dict[str, object]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-slug", required=True)
    parser.add_argument("--to-slug", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        city = resolve_city_by_slug(db, args.from_slug)
        if city is None:
            raise SystemExit(f"Город не найден: {args.from_slug}")
        if city.slug == args.to_slug:
            return {
                "city_id": city.id,
                "old_slug": city.slug,
                "new_slug": args.to_slug,
                "aliases": list(city.slug_aliases or []),
                "already_migrated": True,
            }
        target = db.query(City).filter(City.slug == args.to_slug).first()
        if target is not None and target.id != city.id:
            raise SystemExit(f"Slug занят: {args.to_slug}")
        aliases = list(city.slug_aliases or [])
        if args.from_slug not in aliases:
            aliases.append(args.from_slug)
        preview = {"city_id": city.id, "old_slug": city.slug, "new_slug": args.to_slug, "aliases": aliases}
        if args.apply:
            city.slug_aliases = aliases
            city.slug = args.to_slug
            db.commit()
        return preview


if __name__ == "__main__":
    import json
    print(json.dumps(run(), ensure_ascii=False, indent=2))
