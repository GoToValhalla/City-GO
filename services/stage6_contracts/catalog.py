from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.place import Place
from services.admin_place_update_service import update_admin_place_fields


@dataclass(frozen=True)
class CatalogPlaceUpdate:
    place_id: int
    fields: dict[str, object]
    actor: str


def update_catalog_place(
    db: Session, command: CatalogPlaceUpdate, *, commit: bool = False, locked_place: Place | None = None,
) -> Place | None:
    """Canonical ordinary-field command; caller explicitly owns commit by default."""

    return update_admin_place_fields(
        db, command.place_id, command.fields, actor=command.actor,
        commit=commit, locked_place=locked_place,
    )


def set_destination_assignment_state(
    db: Session, place_id: int, *, primary_destination_id: int | None = None,
    assignment_stale: bool | None = None,
) -> Place | None:
    """Catalog-owned write endpoint for Destination's scalar place references."""

    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        return None
    if primary_destination_id is not None:
        place.primary_destination_id = primary_destination_id
    if assignment_stale is not None:
        place.destination_assignment_stale = assignment_stale
    db.flush()
    return place
