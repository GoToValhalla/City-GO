#!/usr/bin/env python3
"""Enable legacy-disabled import scopes that should refresh by default."""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from db.session import SessionLocal
from models.city import City
from models.city_import_scope import CityImportScope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", help="Optional city slug")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with SessionLocal() as db:
        query = (
            db.query(CityImportScope)
            .join(City, City.id == CityImportScope.city_id)
            .filter(CityImportScope.enabled.is_(False))
            .filter(CityImportScope.status != "paused")
            .filter(CityImportScope.bbox.isnot(None))
        )
        if args.city:
            query = query.filter(City.slug == args.city)

        scopes = query.order_by(City.slug, CityImportScope.priority, CityImportScope.code).all()
        changed = []
        now = datetime.utcnow()
        for scope in scopes:
            city = db.query(City).filter(City.id == scope.city_id).first()
            scope.enabled = True
            scope.updated_at = now
            changed.append({
                "city": city.slug if city else scope.city_id,
                "scope": scope.code,
                "profile": scope.import_profile,
            })

        db.commit()

    print(json.dumps({"enabled_scopes": len(changed), "items": changed}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
