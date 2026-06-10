"""CLI: опубликовать город (launch_status=published, is_active=true)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from services.admin_city_publish_service import publish_city_for_users


def _resolve_slug(db, slug: str | None, name_hint: str | None) -> str:
    if slug:
        return slug
    query = db.query(City)
    if name_hint:
        city = query.filter(City.name.ilike(f"%{name_hint}%")).order_by(City.id.desc()).first()
        if city:
            return city.slug
    for candidate in ("almaty", "алматы"):
        if db.query(City).filter(City.slug == candidate).first():
            return candidate
    raise SystemExit("Укажите --city-slug или --name-hint (город не найден)")


def main() -> None:
    p = argparse.ArgumentParser(description="Publish city for public catalog")
    p.add_argument("--city-slug", default=None)
    p.add_argument("--name-hint", default=None, help="Например: Алматы")
    p.add_argument("--country", default=None)
    p.add_argument("--timezone", default=None)
    p.add_argument("--actor", default="script:publish_city")
    args = p.parse_args()
    db = SessionLocal()
    try:
        slug = _resolve_slug(db, args.city_slug, args.name_hint)
        city = publish_city_for_users(
            db,
            city_slug=slug,
            actor=args.actor,
            country=args.country,
            timezone=args.timezone,
        )
        print(f"CITY_SLUG={city.slug}")
        print(f"CITY_NAME={city.name}")
        print(f"LAUNCH_STATUS={city.launch_status}")
        print(f"IS_ACTIVE={city.is_active}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
