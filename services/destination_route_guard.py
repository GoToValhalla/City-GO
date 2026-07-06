"""Walking / trip-type guards for destination-first routes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from services.city_destination_compatibility import get_destination_by_slug


WALKING_DESTINATION_TYPES = frozenset({"city", "tourist_cluster"})
REGION_TYPES = frozenset({"region", "natural_region", "national_park", "remote_area", "route_corridor"})


def validate_trip_type_for_destination(
    db: Session,
    *,
    destination_slug: str | None,
    destination_id: int | None,
    trip_type: str = "walking",
) -> str | None:
    if trip_type != "walking":
        if trip_type in {"car_daytrip", "expedition"}:
            return "unsupported_trip_type"
        return None
    dest = None
    if destination_id is not None:
        dest = db.query(Destination).filter(Destination.id == destination_id).first()
    elif destination_slug:
        dest = get_destination_by_slug(db, destination_slug)
    if dest is None:
        return None
    if dest.destination_type in WALKING_DESTINATION_TYPES:
        return None
    if dest.destination_type in REGION_TYPES:
        walkable = (
            db.query(DestinationScope.id)
            .filter(
                DestinationScope.destination_id == dest.id,
                DestinationScope.is_walkable_cluster.is_(True),
                DestinationScope.enabled.is_(True),
            )
            .limit(1)
            .first()
        )
        if walkable is None:
            return "walking_not_supported_for_destination"
    return None
