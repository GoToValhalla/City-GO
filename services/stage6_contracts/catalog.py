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
