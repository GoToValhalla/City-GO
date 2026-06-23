"""Field-level confidence API for import/enrichment pipeline."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place_field_confidence import PlaceFieldConfidence

PROTECTED_SOURCES = {"manual", "human_verified", "verified_manual", "admin_manual"}


def level_for(value: float) -> str:
    if value >= 0.8:
        return "high"
    if value >= 0.5:
        return "medium"
    return "low"


def is_protected(row: PlaceFieldConfidence | None) -> bool:
    if row is None:
        return False
    return bool(row.is_manual_verified or row.source_type in PROTECTED_SOURCES)


def upsert_field_confidence(
    db: Session,
    *,
    place_id: int,
    field_name: str,
    confidence: float,
    source_type: str,
    freshness_status: str = "fresh",
    conflict_status: str = "none",
    raw_value: dict[str, object] | None = None,
) -> tuple[PlaceFieldConfidence, bool]:
    row = _get(db, place_id, field_name)
    if is_protected(row):
        return row, False
    row = row or PlaceFieldConfidence(place_id=place_id, field_name=field_name)
    row.confidence = min(max(confidence, 0.0), 1.0)
    row.confidence_level = level_for(row.confidence)
    row.source_type = source_type
    row.freshness_status = freshness_status
    row.conflict_status = conflict_status
    row.raw_value = raw_value
    db.add(row)
    return row, True


def list_field_confidence(db: Session, place_id: int) -> list[PlaceFieldConfidence]:
    return (
        db.query(PlaceFieldConfidence)
        .filter(PlaceFieldConfidence.place_id == place_id)
        .order_by(PlaceFieldConfidence.field_name.asc())
        .all()
    )


def _get(db: Session, place_id: int, field_name: str) -> PlaceFieldConfidence | None:
    # Test and batch sessions can disable autoflush. Reuse a matching pending row
    # before querying the database, otherwise two pipeline steps can insert the
    # same unique (place_id, field_name) pair in one transaction.
    for pending in db.new:
        if (
            isinstance(pending, PlaceFieldConfidence)
            and pending.place_id == place_id
            and pending.field_name == field_name
        ):
            return pending
    return (
        db.query(PlaceFieldConfidence)
        .filter(PlaceFieldConfidence.place_id == place_id, PlaceFieldConfidence.field_name == field_name)
        .first()
    )
