"""Store field-level source evidence for imported or enriched place values."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from models.data_foundation import PlaceFieldProvenance
from models.place import Place

SOURCE_FIELD_TTL_DAYS = {
    "opening_hours": 30,
    "phone": 90,
    "website": 90,
    "address": 180,
}


def record_place_field_provenance(
    db: Session,
    *,
    place: Place,
    source: str,
    source_url: str | None,
    values: dict[str, object],
    obtained_at: datetime | None = None,
) -> None:
    observed_at = obtained_at or datetime.utcnow()
    for field_name, value in values.items():
        if value in (None, "", {}):
            continue
        row = (
            db.query(PlaceFieldProvenance)
            .filter(
                PlaceFieldProvenance.place_id == place.id,
                PlaceFieldProvenance.field_name == field_name,
                PlaceFieldProvenance.source == source,
            )
            .first()
        )
        if row is None:
            row = PlaceFieldProvenance(
                place_id=place.id,
                field_name=field_name,
                source=source,
            )
            db.add(row)

        row.source_url = source_url
        row.confidence = 0.7
        row.freshness_status = "fresh"
        row.obtained_at = observed_at
        row.expires_at = (
            observed_at + timedelta(days=SOURCE_FIELD_TTL_DAYS[field_name])
            if field_name in SOURCE_FIELD_TTL_DAYS
            else None
        )
        row.raw_value = {"value": _serializable(value)}
        row.normalized_value = {"value": _serializable(value)}


def _serializable(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
