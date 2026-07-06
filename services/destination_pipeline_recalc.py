from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationMembershipConflict, DestinationPlaceMembership, DestinationScope
from models.place import Place
from services.destination_bbox import point_in_bbox
from services.destination_membership_service import upsert_membership
from services.destination_pipeline_counters import add_counter

MANUAL_ASSIGNMENTS = frozenset({"manual", "legacy_city"})


def recalculate_destination_memberships(db: Session, destination: Destination, counters: dict[str, int], scope_ids: list[int] | None = None) -> dict[str, int]:
    scopes = _scopes(db, destination.id, scope_ids)
    places = db.query(Place).filter(Place.is_active.is_(True)).all()
    assigned = 0
    conflicts = 0
    for place in places:
        matches = [scope for scope in scopes if scope.bbox and point_in_bbox(place.lat, place.lng, scope.bbox)]
        if not matches or _manual_exists(db, place.id, destination.id):
            continue
        if _ambiguous(matches):
            _conflict(db, place.id, destination.id, matches)
            conflicts += 1
            add_counter(counters, "errors_count")
            continue
        before = _membership_exists(db, place.id, destination.id)
        scope = sorted(matches, key=lambda row: (-row.priority, row.id))[0]
        upsert_membership(db, place_id=place.id, destination_id=destination.id, assignment_type="spatial", is_primary=place.primary_destination_id in (None, destination.id), confidence=0.84, source="destination_recalc", scope_id=scope.id)
        add_counter(counters, "memberships_updated" if before else "memberships_created")
        assigned += 1
    db.flush()
    return {"assigned": assigned, "conflicts": conflicts}


def _scopes(db: Session, destination_id: int, scope_ids: list[int] | None) -> list[DestinationScope]:
    query = db.query(DestinationScope).filter(DestinationScope.destination_id == destination_id, DestinationScope.enabled.is_(True))
    if scope_ids:
        query = query.filter(DestinationScope.id.in_(scope_ids))
    return query.order_by(DestinationScope.priority.desc(), DestinationScope.id.asc()).all()


def _manual_exists(db: Session, place_id: int, destination_id: int) -> bool:
    return db.query(DestinationPlaceMembership.id).filter(DestinationPlaceMembership.place_id == place_id, DestinationPlaceMembership.destination_id == destination_id, DestinationPlaceMembership.assignment_type.in_(tuple(MANUAL_ASSIGNMENTS)), DestinationPlaceMembership.invalidated_at.is_(None)).first() is not None


def _membership_exists(db: Session, place_id: int, destination_id: int) -> bool:
    return db.query(DestinationPlaceMembership.id).filter_by(place_id=place_id, destination_id=destination_id).first() is not None


def _ambiguous(scopes: list[DestinationScope]) -> bool:
    return len(scopes) > 1 and len({scope.priority for scope in scopes}) == 1


def _conflict(db: Session, place_id: int, destination_id: int, scopes: list[DestinationScope]) -> None:
    exists = db.query(DestinationMembershipConflict.id).filter_by(place_id=place_id, destination_id=destination_id, status="open").first()
    if exists is None:
        db.add(DestinationMembershipConflict(place_id=place_id, destination_id=destination_id, scope_ids=[scope.id for scope in scopes], reason="overlapping_scopes_equal_priority", status="open"))
