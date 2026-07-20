"""Destination CRUD and listing."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.place import Place
from services.place_public_visibility import public_place_conditions


def list_published_destinations(db: Session, *, limit: int = 100, offset: int = 0) -> list[Destination]:
    return (
        db.query(Destination)
        .filter(Destination.is_active.is_(True), Destination.is_published.is_(True))
        .order_by(Destination.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_published_destinations(db: Session) -> int:
    return int(
        db.query(func.count(Destination.id))
        .filter(Destination.is_active.is_(True), Destination.is_published.is_(True))
        .scalar()
        or 0
    )


def count_places_for_destination(db: Session, destination_id: int) -> int:
    return int(
        db.query(func.count(DestinationPlaceMembership.id))
        .join(Place, Place.id == DestinationPlaceMembership.place_id)
        .filter(
            DestinationPlaceMembership.destination_id == destination_id,
            DestinationPlaceMembership.is_hidden.is_(False),
            DestinationPlaceMembership.invalidated_at.is_(None),
            *public_place_conditions(),
        )
        .scalar()
        or 0
    )


def has_children(db: Session, destination_id: int) -> bool:
    return (
        db.query(Destination.id)
        .filter(
            Destination.parent_id == destination_id,
            Destination.is_active.is_(True),
            Destination.is_published.is_(True),
        )
        .limit(1)
        .first()
        is not None
    )


def list_children(db: Session, parent_id: int) -> list[Destination]:
    return (
        db.query(Destination)
        .filter(
            Destination.parent_id == parent_id,
            Destination.is_active.is_(True),
            Destination.is_published.is_(True),
        )
        .order_by(Destination.name.asc())
        .all()
    )


def list_scopes(db: Session, destination_id: int) -> list[DestinationScope]:
    return (
        db.query(DestinationScope)
        .filter(DestinationScope.destination_id == destination_id)
        .order_by(DestinationScope.priority.desc(), DestinationScope.id.asc())
        .all()
    )


def create_destination(db: Session, payload: dict[str, object]) -> Destination:
    row = Destination(**payload)
    db.add(row)
    db.flush()
    return row
