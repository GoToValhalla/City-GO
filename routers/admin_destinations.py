"""Admin Destination management v1."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
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
    DestinationScopeSummary,
)
from schemas.destination_geo import (
    AdminDestinationFromGeoCandidateRequest,
    AdminScopeFromGeoCandidateRequest,
    DestinationGeoSearchResponse,
)
from services.destination_admin_mutations import create as create_destination_record
from services.destination_admin_mutations import update as update_destination_record
from services.destination_admin_queries import conflicts, detail, destinations, memberships, orphan_places, scopes
from services.destination_admin_validation import (
    ValidationIssue,
    validate_bbox,
    validate_coordinates,
    validate_destination_type,
    validate_required_text,
    validate_slug,
)
from services.destination_membership_application import assign as assign_membership
from services.destination_membership_application import hide as hide_destination_membership
from services.destination_geo_candidate_service import (
    build_destination_payload,
    candidate_from_input,
    search_destination_geo_candidates,
    to_read_model,
)
from services.destination_scope_application import create as create_scope_record
from services.destination_scope_application import delete as delete_scope_record
from services.destination_scope_application import recover as recover_scope_record
from services.destination_scope_application import update as update_scope_record


router = APIRouter(prefix="/admin/destinations", tags=["admin-destinations"])


@router.get("/orphans/places")
def admin_orphan_places(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    return orphan_places(db, limit)


@router.get("/conflicts/list")
def admin_membership_conflicts(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    return conflicts(db, limit)


@router.get("/geo-search", response_model=DestinationGeoSearchResponse)
def admin_destination_geo_search(
    auth: AdminContext = Depends(admin_required),
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=5, ge=1, le=20),
) -> DestinationGeoSearchResponse:
    items = [to_read_model(row) for row in search_destination_geo_candidates(q, limit=limit)]
    return DestinationGeoSearchResponse(query=q.strip(), items=items)


@router.post("/from-geo-candidate", response_model=DestinationDetail)
def admin_create_destination_from_geo_candidate(
    payload: AdminDestinationFromGeoCandidateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    try:
        candidate = candidate_from_input(payload.candidate)
        data = build_destination_payload(
            candidate,
            slug=payload.slug,
            name=payload.name,
            destination_type=payload.destination_type,
        )
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    try:
        return create_destination_record(db, data, actor=auth.actor_id,
            action="destination_created_from_geo", context={"candidate_key": candidate.candidate_key})
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=DestinationListResponse)
def admin_list_destinations(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DestinationListResponse:
    return destinations(db, limit=limit, offset=offset)


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
    try:
        return create_destination_record(db, data, actor=auth.actor_id, action="destination_created")
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{slug}", response_model=DestinationDetail)
def admin_update_destination(
    slug: str,
    payload: AdminDestinationUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    try:
        data = _destination_update_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    try:
        return update_destination_record(db, slug, data, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{slug}", response_model=DestinationDetail)
def read_destination_admin(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDetail:
    try:
        return detail(db, slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{slug}/scopes")
def admin_list_scopes(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        return scopes(db, slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{slug}/scopes")
def admin_create_scope(
    slug: str,
    payload: AdminDestinationScopeCreate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        data = _scope_create_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    try:
        return create_scope_record(db, slug, data, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{slug}/scopes/from-geo-candidate")
def admin_scope_from_geo_candidate(
    slug: str,
    payload: AdminScopeFromGeoCandidateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        candidate = candidate_from_input(payload.candidate)
        return recover_scope_record(db, slug, candidate, payload, actor=auth.actor_id)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{slug}/scopes/{scope_id}")
def admin_update_scope(
    slug: str,
    scope_id: int,
    payload: AdminDestinationScopeUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        data = _scope_update_data(payload)
    except ValidationIssue as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    try:
        return update_scope_record(db, slug, scope_id, data, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{slug}/scopes/{scope_id}")
def admin_delete_scope(
    slug: str,
    scope_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        return delete_scope_record(db, slug, scope_id, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{slug}/memberships", response_model=list[DestinationMembershipRead])
def admin_list_memberships(
    slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return memberships(db, slug, limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{slug}/assign-place")
def admin_assign_place(
    slug: str,
    payload: AdminAssignPlaceRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        return assign_membership(db, slug, payload.place_id, primary=payload.is_primary, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{slug}/hide-place")
def admin_hide_place(
    slug: str,
    payload: AdminHidePlaceRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        return hide_destination_membership(db, slug, payload.place_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
