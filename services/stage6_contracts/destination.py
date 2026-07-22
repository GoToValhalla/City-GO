from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.destination import DestinationPlaceMembership
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_membership_service import (
    get_place_ids_for_destination,
    hide_membership,
    upsert_membership,
)


@dataclass(frozen=True)
class DestinationMembershipCommand:
    place_id: int
    destination_id: int
    assignment_type: str = "legacy_city"
    is_primary: bool = False
    confidence: float = 1.0
    source: str | None = None
    scope_id: int | None = None


def assign_place(db: Session, command: DestinationMembershipCommand) -> DestinationPlaceMembership:
    return upsert_membership(db, **command.__dict__)


def hide_place(db: Session, *, place_id: int, destination_id: int) -> bool:
    return hide_membership(db, place_id=place_id, destination_id=destination_id)


def destination_place_ids(db: Session, destination_id: int) -> tuple[int, ...]:
    return tuple(get_place_ids_for_destination(db, destination_id))


def published_destination_id(db: Session, slug: str) -> int | None:
    destination = get_destination_by_slug(db, slug)
    if destination is None or not destination.is_active or not destination.is_published:
        return None
    return int(destination.id)


def destination_id_by_slug(db: Session, slug: str) -> int | None:
    destination = get_destination_by_slug(db, slug)
    return int(destination.id) if destination is not None else None
