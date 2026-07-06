"""Admin Destination management v1."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.destination import Destination, DestinationMembershipConflict, DestinationPlaceMembership, DestinationScope
from models.place import Place
from routers.destinations import _to_list_item, read_destination
from schemas.destination import (
    AdminAssignPlaceRequest,
    AdminDestinationCreate,
    AdminDestinationScopeCreate,
    AdminHidePlaceRequest,
    DestinationDetail,
    DestinationListResponse,
    DestinationMembershipRead,
)
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_membership_service import hide_membership, upsert_membership
from services.destination_service import create_destination, list_scopes

router = APIRouter(prefix="/admin/destinations", tags=["admin-destinations"])


@router.get("/orphans/places")
def admin_orphan_places(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    subq = db.query(DestinationPlaceMembership.place_id)
    rows = db.query(Place).filter(~Place.id.in_(subq)).limit(limit).all()
    return [{"id": p.id, "slug": p.slug, "title": p.title, "city_id": p.city_id} for p in rows]


@router.get("/conflicts/list")
def admin_membership_conflicts(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    rows = (
        db.query(DestinationMembershipConflict)
        .filter(DestinationMembershipConflict.status == "open")
        .order_by(DestinationMembershipConflict.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "place_id": row.place_id,
            "destination_id": row.destination_id,
            "scope_ids": row.scope_ids,
            "reason": row.reason,
        }
        for row in rows
    ]


@router.get("", response_model=DestinationListResponse)
def admin_list_destinations(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DestinationListResponse:
    rows = db.query(Destination).order_by(Destination.name.asc()).offset(offset).limit(limit).all()
    total = db.query(Destination).count()
    return DestinationListResponse(items=[_to_list_item(db, row) for row in rows], total=total)


@router.post("", response_model=DestinationDetail)
def admin_create_destination(
    payload: AdminDestinationCreate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    if db.query(Destination).filter(Destination.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="Destination slug already exists")
    row = create_destination(db, payload.model_dump())
    db.commit()
    db.refresh(row)
    return read_destination(row.slug, db=db)


@router.get("/{slug}", response_model=DestinationDetail)
def read_destination_admin(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    return read_destination(slug, db=db)


@router.get("/{slug}/scopes")
def admin_list_scopes(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    return list_scopes(db, dest.id)


@router.post("/{slug}/scopes")
def admin_create_scope(
    slug: str,
    payload: AdminDestinationScopeCreate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    scope = DestinationScope(destination_id=dest.id, **payload.model_dump())
    db.add(scope)
    db.commit()
    db.refresh(scope)
    return scope


@router.get("/{slug}/memberships", response_model=list[DestinationMembershipRead])
def admin_list_memberships(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    rows = (
        db.query(DestinationPlaceMembership)
        .filter(DestinationPlaceMembership.destination_id == dest.id)
        .order_by(DestinationPlaceMembership.id.desc())
        .limit(limit)
        .all()
    )
    return rows


@router.post("/{slug}/assign-place")
def admin_assign_place(
    slug: str,
    payload: AdminAssignPlaceRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    if db.query(Place).filter(Place.id == payload.place_id).first() is None:
        raise HTTPException(status_code=404, detail="Place not found")
    row = upsert_membership(
        db,
        place_id=payload.place_id,
        destination_id=dest.id,
        assignment_type="manual",
        is_primary=payload.is_primary,
        confidence=1.0,
        source=f"admin:{auth.actor_id}",
    )
    db.commit()
    return {"membership_id": row.id}


@router.post("/{slug}/hide-place")
def admin_hide_place(
    slug: str,
    payload: AdminHidePlaceRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    if not hide_membership(db, place_id=payload.place_id, destination_id=dest.id):
        raise HTTPException(status_code=404, detail="Membership not found")
    db.commit()
    return {"hidden": True}
