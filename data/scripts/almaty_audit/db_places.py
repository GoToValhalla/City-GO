"""CSV выгрузка мест Алматы из БД."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_tag import PlaceTag
from models.tag import Tag


def _tags_for(db: Session, place_id: int) -> str:
    rows = (
        db.query(Tag.code)
        .join(PlaceTag, PlaceTag.tag_id == Tag.id)
        .filter(PlaceTag.place_id == place_id)
        .all()
    )
    return ",".join(r[0] for r in rows)


def write_places_full(db: Session, out: Path, slugs: tuple[str, ...]) -> int:
    city = db.query(City).filter(City.slug.in_(slugs)).first()
    if city is None:
        out.write_text("", encoding="utf-8")
        return 0
    fields = [
        "id", "slug", "title", "category", "lat", "lng", "address", "address_source",
        "address_confidence", "address_updated_at", "image_url", "short_description",
        "opening_hours", "source", "source_url", "confidence", "is_published",
        "publication_status", "is_active", "status", "is_visible_in_catalog",
        "is_route_eligible", "route_exclusion_reason", "verification_status", "tags",
        "created_at", "updated_at",
    ]
    places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id).all()
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for p in places:
            row = {k: getattr(p, k, None) for k in fields if hasattr(p, k)}
            row["opening_hours"] = json.dumps(p.opening_hours) if p.opening_hours else None
            row["tags"] = _tags_for(db, p.id)
            w.writerow(row)
    return len(places)
