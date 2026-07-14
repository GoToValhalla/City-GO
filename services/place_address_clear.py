"""Очистка плейсхолдерных адресов без reverse geocoding."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_address_policy import is_placeholder_address, is_real_address
from services.place_change_review_service import propose_place_change


def clear_placeholder_addresses(db: Session, *, city_slug: str, apply: bool) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "mode": "clear_apply" if apply else "clear_dry_run",
        "city": city_slug,
        "checked": 0,
        "cleared": 0,
        "skipped_existing_address": 0,
        "results": [],
    }
    places = (
        db.query(Place)
        .join(City)
        .filter(City.slug == city_slug)
        .order_by(Place.id.asc())
        .all()
    )
    for place in places:
        if is_real_address(place.address):
            stats["skipped_existing_address"] += 1
            continue
        if not is_placeholder_address(place.address):
            continue
        stats["checked"] += 1
        status = "cleared"
        if apply:
            if propose_place_change(db, place=place, proposed={"address": ""}, reason="placeholder_address_cleared"):
                place.address = ""
                place.updated_at = datetime.utcnow()
                db.add(place)
                db.commit()
            else:
                status = "queued_for_review"
                db.commit()
        stats["cleared"] += 1
        results = stats["results"]
        if isinstance(results, list) and len(results) < 10:
            results.append({"place_id": place.id, "title": place.title, "status": status})
    return stats
