"""DestinationPlaceMembership operations."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.destination import DestinationPlaceMembership
from services.stage6_contracts.catalog import set_destination_assignment_state


def upsert_membership(
    db: Session,
    *,
    place_id: int,
    destination_id: int,
    assignment_type: str = "legacy_city",
    is_primary: bool = False,
    confidence: float = 1.0,
    source: str | None = None,
    scope_id: int | None = None,
) -> DestinationPlaceMembership:
    row = (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.destination_id == destination_id,
        )
        .first()
    )
    if row is None:
        row = DestinationPlaceMembership(
            place_id=place_id,
            destination_id=destination_id,
            assignment_type=assignment_type,
            is_primary=is_primary,
            confidence=confidence,
            source=source,
            scope_id=scope_id,
        )
        db.add(row)
    else:
        row.assignment_type = assignment_type
        row.confidence = confidence
        row.source = source or row.source
        row.scope_id = scope_id or row.scope_id
        row.invalidated_at = None
        if is_primary:
            row.is_primary = True
    if is_primary:
        _clear_other_primary(db, place_id=place_id, keep_destination_id=destination_id)
        set_destination_assignment_state(db, place_id, primary_destination_id=destination_id)
    db.flush()
    return row


def hide_membership(db: Session, *, place_id: int, destination_id: int) -> bool:
    row = (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.destination_id == destination_id,
        )
        .first()
    )
    if row is None:
        return False
    row.is_hidden = True
    db.flush()
    return True


def get_place_ids_for_destination(db: Session, destination_id: int) -> list[int]:
    rows = (
        db.query(DestinationPlaceMembership.place_id)
        .filter(
            DestinationPlaceMembership.destination_id == destination_id,
            DestinationPlaceMembership.is_hidden.is_(False),
            DestinationPlaceMembership.invalidated_at.is_(None),
        )
        .all()
    )
    return [int(row[0]) for row in rows]


def get_destinations_for_place(db: Session, place_id: int) -> list[DestinationPlaceMembership]:
    return (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.is_hidden.is_(False),
            DestinationPlaceMembership.invalidated_at.is_(None),
        )
        .all()
    )


def mark_place_stale(db: Session, place_id: int) -> None:
    set_destination_assignment_state(db, place_id, assignment_stale=True)


def _clear_other_primary(db: Session, *, place_id: int, keep_destination_id: int) -> None:
    rows = (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.is_primary.is_(True),
            DestinationPlaceMembership.destination_id != keep_destination_id,
        )
        .all()
    )
    for row in rows:
        row.is_primary = False


def invalidate_spatial_memberships(db: Session, place_id: int) -> None:
    now = datetime.utcnow()
    rows = (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.assignment_type.in_(("spatial", "imported", "route_corridor")),
        )
        .all()
    )
    for row in rows:
        row.invalidated_at = now
