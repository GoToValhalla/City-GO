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
    AdminDestinationScopeUpdate,
    AdminDestinationUpdate,
    AdminHidePlaceRequest,
    DestinationDetail,
    DestinationListResponse,
    DestinationMembershipRead,
)
from services.admin_audit_service import write_admin_audit_log
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_admin_validation import (
    ValidationIssue,
    validate_bbox,
    validate_coordinates,
    validate_destination_type,
    validate_required_text,
    validate_slug,
)
from services.destination_data_pipeline_service import active_destination_run
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
    try:
        data = _destination_create_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    if db.query(Destination).filter(Destination.slug == data["slug"]).first():
        raise HTTPException(status_code=409, detail="Destination slug already exists")
    row = create_destination(db, data)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_created", entity_type="destination", entity_id=row.id, new_value=data)
    db.commit()
    db.refresh(row)
    return read_destination(row.slug, db=db)


@router.patch("/{slug}", response_model=DestinationDetail)
def admin_update_destination(
    slug: str,
    payload: AdminDestinationUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    dest = _destination_or_404(db, slug)
    old = _destination_snapshot(dest)
    try:
        data = _destination_update_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    if "slug" in data and data["slug"] != dest.slug and db.query(Destination).filter(Destination.slug == data["slug"]).first():
        raise HTTPException(status_code=409, detail="Destination slug already exists")
    for key, value in data.items():
        setattr(dest, key, value)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_updated", entity_type="destination", entity_id=dest.id, old_value=old, new_value=_destination_snapshot(dest))
    db.commit()
    db.refresh(dest)
    return read_destination(dest.slug, db=db)


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
    dest = _destination_or_404(db, slug)
    try:
        data = _scope_create_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    if _scope_code_exists(db, dest.id, str(data["code"])):
        raise HTTPException(status_code=409, detail="Scope code already exists")
    scope = DestinationScope(destination_id=dest.id, **data)
    db.add(scope)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_scope_created", entity_type="destination_scope", entity_id=None, new_value=data | {"destination_id": dest.id})
    db.commit()
    db.refresh(scope)
    return scope


@router.patch("/{slug}/scopes/{scope_id}")
def admin_update_scope(
    slug: str,
    scope_id: int,
    payload: AdminDestinationScopeUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = _destination_or_404(db, slug)
    scope = _scope_or_404(db, dest.id, scope_id)
    old = _scope_snapshot(scope)
    try:
        data = _scope_update_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    if "code" in data and data["code"] != scope.code and _scope_code_exists(db, dest.id, str(data["code"])):
        raise HTTPException(status_code=409, detail="Scope code already exists")
    for key, value in data.items():
        setattr(scope, key, value)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_scope_updated", entity_type="destination_scope", entity_id=scope.id, old_value=old, new_value=_scope_snapshot(scope))
    db.commit()
    db.refresh(scope)
    return scope


@router.delete("/{slug}/scopes/{scope_id}")
def admin_delete_scope(
    slug: str,
    scope_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    dest = _destination_or_404(db, slug)
    scope = _scope_or_404(db, dest.id, scope_id)
    if active_destination_run(db, dest.id) is not None:
        raise HTTPException(status_code=409, detail="Нельзя удалить контур во время активного прогона")
    snapshot = _scope_snapshot(scope)
    db.delete(scope)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_scope_deleted", entity_type="destination_scope", entity_id=scope.id, old_value=snapshot)
    db.commit()
    return {"deleted": True}


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


def _destination_or_404(db: Session, slug: str) -> Destination:
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Destination not found")
    return dest


def _destination_create_data(payload: AdminDestinationCreate) -> dict[str, object]:
    data = payload.model_dump()
    data["slug"] = validate_slug(str(data["slug"]))
    data["name"] = validate_required_text(str(data["name"]), "Название")
    data["destination_type"] = validate_destination_type(str(data.get("destination_type") or "region"))
    validate_coordinates(data.get("center_lat"), data.get("center_lng"))
    data["bbox"] = validate_bbox(data.get("bbox"))
    return data


def _destination_update_data(payload: AdminDestinationUpdate) -> dict[str, object]:
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        data["slug"] = validate_slug(str(data["slug"]))
    if "name" in data and data["name"] is not None:
        data["name"] = validate_required_text(str(data["name"]), "Название")
    if "destination_type" in data and data["destination_type"] is not None:
        data["destination_type"] = validate_destination_type(str(data["destination_type"]))
    validate_coordinates(data.get("center_lat"), data.get("center_lng"))
    if "bbox" in data:
        data["bbox"] = validate_bbox(data.get("bbox"))
    return data


def _scope_create_data(payload: AdminDestinationScopeCreate) -> dict[str, object]:
    data = payload.model_dump()
    data["code"] = validate_slug(str(data["code"]))
    data["name"] = validate_required_text(str(data["name"]), "Название контура")
    data["bbox"] = validate_bbox(data.get("bbox"))
    return data


def _scope_update_data(payload: AdminDestinationScopeUpdate) -> dict[str, object]:
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] is not None:
        data["code"] = validate_slug(str(data["code"]))
    if "name" in data and data["name"] is not None:
        data["name"] = validate_required_text(str(data["name"]), "Название контура")
    if "bbox" in data:
        data["bbox"] = validate_bbox(data.get("bbox"))
    return data


def _scope_or_404(db: Session, destination_id: int, scope_id: int) -> DestinationScope:
    scope = db.query(DestinationScope).filter_by(destination_id=destination_id, id=scope_id).first()
    if scope is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    return scope


def _scope_code_exists(db: Session, destination_id: int, code: str) -> bool:
    return db.query(DestinationScope.id).filter_by(destination_id=destination_id, code=code).first() is not None


def _destination_snapshot(dest: Destination) -> dict[str, object]:
    return {key: getattr(dest, key) for key in ("slug", "name", "destination_type", "center_lat", "center_lng", "bbox", "launch_status", "is_published", "is_active")}


def _scope_snapshot(scope: DestinationScope) -> dict[str, object]:
    return {key: getattr(scope, key) for key in ("code", "name", "scope_type", "import_strategy", "bbox", "import_profile", "priority", "enabled")}
