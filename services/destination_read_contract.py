from __future__ import annotations

from sqlalchemy.orm import Session

from schemas.destination import DestinationCenter, DestinationListItem
from services.destination_service import count_places_for_destination, has_children


def destination_list_item(db: Session, row) -> DestinationListItem:
    return DestinationListItem(
        id=row.id, slug=row.slug, title=row.name, destination_type=row.destination_type,
        parent_id=row.parent_id, center=DestinationCenter(lat=row.center_lat, lng=row.center_lng),
        readiness_score=row.readiness_score, has_children=has_children(db, row.id),
        places_count=count_places_for_destination(db, row.id),
    )
