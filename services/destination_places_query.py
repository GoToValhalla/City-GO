"""Place list queries via destination membership (no ST_Contains hot path)."""

from __future__ import annotations

from sqlalchemy.orm import Query, Session

from models.destination import DestinationPlaceMembership
from models.place import Place
from services.destination_flags import destination_catalog_reads_enabled
from services.place_public_visibility import apply_public_place_visibility


def apply_destination_membership_filter(
    db: Session,
    query: Query,
    destination_id: int,
) -> Query:
    query = query.join(
        DestinationPlaceMembership,
        DestinationPlaceMembership.place_id == Place.id,
    ).filter(
        DestinationPlaceMembership.destination_id == destination_id,
        DestinationPlaceMembership.is_hidden.is_(False),
        DestinationPlaceMembership.invalidated_at.is_(None),
    )
    return apply_public_place_visibility(query)


def should_use_membership_catalog() -> bool:
    return destination_catalog_reads_enabled()
