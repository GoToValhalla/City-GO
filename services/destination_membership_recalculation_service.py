"""Membership recalculation (bbox v1, no PostGIS hot path)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationMembershipConflict, DestinationScope
from models.place import Place
from services.destination_bbox import point_in_bbox
from services.destination_membership_service import invalidate_spatial_memberships, upsert_membership


MANUAL_TYPES = frozenset({"manual", "legacy_city"})


def recalculate_place_memberships(db: Session, place_id: int) -> dict[str, int]:
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        return {"assigned": 0, "conflicts": 0}
    invalidate_spatial_memberships(db, place_id)
    assigned = 0
    conflicts = 0
    matches: list[tuple[DestinationScope, Destination]] = []
    scopes = (
        db.query(DestinationScope, Destination)
        .join(Destination, DestinationScope.destination_id == Destination.id)
        .filter(DestinationScope.enabled.is_(True), Destination.is_active.is_(True))
        .all()
    )
    for scope, dest in scopes:
        if scope.bbox and point_in_bbox(place.lat, place.lng, scope.bbox):
            matches.append((scope, dest))
    by_dest: dict[int, list[DestinationScope]] = {}
    for scope, dest in matches:
        by_dest.setdefault(dest.id, []).append(scope)
    for dest_id, dest_scopes in by_dest.items():
        if len(dest_scopes) > 1 and _same_priority(dest_scopes):
            _record_conflict(db, place_id, dest_id, dest_scopes)
            conflicts += 1
            continue
        scope = sorted(dest_scopes, key=lambda s: (-s.priority, s.id))[0]
        dest = db.query(Destination).filter(Destination.id == dest_id).first()
        if dest is None:
            continue
        if _has_manual_membership(db, place_id, dest_id):
            continue
        upsert_membership(
            db,
            place_id=place_id,
            destination_id=dest_id,
            assignment_type="spatial",
            is_primary=place.primary_destination_id in (None, dest_id),
            confidence=0.85,
            source="bbox_recalc",
            scope_id=scope.id,
        )
        assigned += 1
    place.destination_assignment_stale = False
    db.flush()
    return {"assigned": assigned, "conflicts": conflicts}


def _has_manual_membership(db: Session, place_id: int, destination_id: int) -> bool:
    from models.destination import DestinationPlaceMembership

    row = (
        db.query(DestinationPlaceMembership)
        .filter(
            DestinationPlaceMembership.place_id == place_id,
            DestinationPlaceMembership.destination_id == destination_id,
            DestinationPlaceMembership.assignment_type.in_(tuple(MANUAL_TYPES)),
            DestinationPlaceMembership.invalidated_at.is_(None),
        )
        .first()
    )
    return row is not None


def _same_priority(scopes: list[DestinationScope]) -> bool:
    priorities = {s.priority for s in scopes}
    return len(priorities) == 1 and len(scopes) > 1


def _record_conflict(db: Session, place_id: int, destination_id: int, scopes: list[DestinationScope]) -> None:
    row = DestinationMembershipConflict(
        place_id=place_id,
        destination_id=destination_id,
        scope_ids=[s.id for s in scopes],
        reason="overlapping_scopes_equal_priority",
        status="open",
    )
    db.add(row)
