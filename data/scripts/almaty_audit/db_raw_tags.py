"""Sample raw OSM tags для Алматы."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.source_observation import SourceObservation


def write_raw_tags_sample(db: Session, out: Path, slugs: tuple[str, ...], limit: int = 800) -> int:
    city = db.query(City).filter(City.slug.in_(slugs)).first()
    if city is None:
        out.write_text("", encoding="utf-8")
        return 0
    fields = ["id", "title", "category", "lat", "lng", "address", "raw_osm_tags", "source", "source_url"]
    places = (
        db.query(Place)
        .filter(Place.city_id == city.id)
        .order_by(Place.id.desc())
        .limit(limit)
        .all()
    )
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in places:
            obs = (
                db.query(SourceObservation)
                .filter(SourceObservation.canonical_place_id == p.id)
                .order_by(SourceObservation.id.desc())
                .first()
            )
            payload = obs.raw_payload if obs else {}
            tags = payload.get("tags") if isinstance(payload, dict) else payload
            w.writerow({
                "id": p.id, "title": p.title, "category": p.category,
                "lat": p.lat, "lng": p.lng, "address": p.address,
                "raw_osm_tags": json.dumps(tags, ensure_ascii=False) if tags else None,
                "source": p.source, "source_url": p.source_url,
            })
    return len(places)
