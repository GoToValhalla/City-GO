from __future__ import annotations

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationMembershipConflict, DestinationPlaceMembership
from models.place import Place
from schemas.destination import (
    DestinationDetail, DestinationListResponse, DestinationMembershipRead, DestinationScopeSummary,
)
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_read_contract import destination_list_item
from services.destination_service import list_scopes


def detail(db: Session, slug: str) -> DestinationDetail:
    row = require_destination(db, slug)
    base = destination_list_item(db, row)
    children = [destination_list_item(db, child) for child in db.query(Destination).filter(
        Destination.parent_id == row.id
    ).order_by(Destination.name.asc()).all()]
    scopes = [DestinationScopeSummary.model_validate(scope) for scope in list_scopes(db, row.id)]
    return DestinationDetail(
        **base.model_dump(), launch_status=row.launch_status, is_published=row.is_published,
        sub_destinations=children, scopes=scopes,
    )


def orphan_places(db: Session, limit: int) -> list[dict[str, object]]:
    assigned = db.query(DestinationPlaceMembership.place_id)
    rows = db.query(Place).filter(~Place.id.in_(assigned)).limit(limit).all()
    return [{"id": row.id, "slug": row.slug, "title": row.title, "city_id": row.city_id} for row in rows]


def conflicts(db: Session, limit: int) -> list[dict[str, object]]:
    rows = db.query(DestinationMembershipConflict).filter(
        DestinationMembershipConflict.status == "open"
    ).order_by(DestinationMembershipConflict.id.desc()).limit(limit).all()
    return [{"id": row.id, "place_id": row.place_id, "destination_id": row.destination_id,
        "scope_ids": row.scope_ids, "reason": row.reason} for row in rows]


def destinations(db: Session, *, limit: int, offset: int) -> DestinationListResponse:
    rows = db.query(Destination).order_by(Destination.name.asc()).offset(offset).limit(limit).all()
    return DestinationListResponse(
        items=[destination_list_item(db, row) for row in rows], total=db.query(Destination).count(),
    )


def scopes(db: Session, slug: str):
    return list_scopes(db, require_destination(db, slug).id)


def memberships(db: Session, slug: str, limit: int) -> list[DestinationMembershipRead]:
    destination = require_destination(db, slug)
    return db.query(DestinationPlaceMembership).filter(
        DestinationPlaceMembership.destination_id == destination.id
    ).order_by(DestinationPlaceMembership.id.desc()).limit(limit).all()


def require_destination(db: Session, slug: str) -> Destination:
    destination = get_destination_by_slug(db, slug)
    if destination is None:
        raise LookupError("Destination not found")
    return destination
