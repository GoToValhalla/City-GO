from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.destination_admin_queries import require_destination
from services.stage6_contracts.destination import (
    DestinationMembershipCommand, assign_place, hide_place,
)


def assign(db: Session, slug: str, place_id: int, *, primary: bool, actor: str) -> dict[str, int]:
    destination = require_destination(db, slug)
    if db.query(Place.id).filter(Place.id == place_id).first() is None:
        raise LookupError("Place not found")
    membership = assign_place(db, DestinationMembershipCommand(
        place_id=place_id, destination_id=destination.id, assignment_type="manual",
        is_primary=primary, source=f"admin:{actor}",
    ))
    db.commit()
    return {"membership_id": membership.id}


def hide(db: Session, slug: str, place_id: int) -> dict[str, bool]:
    destination = require_destination(db, slug)
    if not hide_place(db, place_id=place_id, destination_id=destination.id):
        raise LookupError("Membership not found")
    db.commit()
    return {"hidden": True}
