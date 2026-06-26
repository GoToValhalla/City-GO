"""Freshness policy and review queue for public place data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.data_foundation import PlaceFieldProvenance
from models.place import Place
from services.review_queue_service import ensure_review_item

FRESHNESS_POLICIES: dict[str, int] = {
    "opening_hours": 30,
    "phone": 90,
    "website": 90,
    "address": 180,
}


def enqueue_stale_place_fields(
    db: Session,
    *,
    city_slug: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    checked_at = now or datetime.utcnow()
    query = db.query(Place, City).join(City, City.id == Place.city_id).filter(Place.is_active.is_(True))
    if city_slug:
        query = query.filter(City.slug == city_slug)

    scanned = 0
    queued = 0
    stale_fields_count = 0
    by_city: dict[str, int] = {}
    for place, city in query.all():
        scanned += 1
        stale_fields = _stale_fields(db, place, checked_at)
        place.critical_field_expired = bool(stale_fields)
        if not stale_fields:
            continue

        stale_fields_count += len(stale_fields)
        by_city[city.slug] = by_city.get(city.slug, 0) + 1
        ensure_review_item(
            db,
            city_id=city.id,
            place_id=place.id,
            field_name="field_freshness",
            reason="critical_field_stale",
            severity="high",
            payload={
                "kind": "field_freshness",
                "checked_at": checked_at.isoformat(),
                "fields": stale_fields,
            },
        )
        queued += 1

    db.commit()
    return {
        "scanned_places": scanned,
        "queued_places": queued,
        "stale_fields": stale_fields_count,
        "by_city": by_city,
    }


def _stale_fields(db: Session, place: Place, checked_at: datetime) -> list[dict[str, object]]:
    stale: list[dict[str, object]] = []
    for field_name, max_age_days in FRESHNESS_POLICIES.items():
        value = getattr(place, field_name)
        if value in (None, "", {}):
            continue
        provenance = (
            db.query(PlaceFieldProvenance)
            .filter(
                PlaceFieldProvenance.place_id == place.id,
                PlaceFieldProvenance.field_name == field_name,
            )
            .order_by(PlaceFieldProvenance.obtained_at.desc(), PlaceFieldProvenance.id.desc())
            .first()
        )
        observed_at = _observed_at(place, field_name, provenance)
        expired = (
            provenance is not None
            and provenance.expires_at is not None
            and provenance.expires_at <= checked_at
        )
        if not expired and observed_at + timedelta(days=max_age_days) > checked_at:
            continue
        stale.append(
            {
                "field": field_name,
                "value": _serializable_value(value),
                "source": provenance.source if provenance else "legacy_unattributed",
                "source_url": provenance.source_url if provenance else None,
                "observed_at": observed_at.isoformat(),
                "max_age_days": max_age_days,
                "expires_at": provenance.expires_at.isoformat() if provenance and provenance.expires_at else None,
            }
        )
    return stale


def _observed_at(
    place: Place,
    field_name: str,
    provenance: PlaceFieldProvenance | None,
) -> datetime:
    if provenance is not None:
        return provenance.obtained_at
    if field_name == "address" and place.address_updated_at is not None:
        return place.address_updated_at
    return place.last_verified_at or place.updated_at or place.created_at


def _serializable_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
