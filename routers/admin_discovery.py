"""Admin region-first destination discovery."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.destination_discovery import (
    BulkCreateRequest,
    BulkCreateResult,
    CandidateListResponse,
    DestinationDiscoveryCandidate,
    DiscoverRegionRequest,
    DiscoverRegionResponse,
    JobDetailResponse,
    RegionSearchResponse,
)
from services.destination_discovery.bulk_create import bulk_create_from_job
from services.destination_discovery.orchestrator import (
    get_candidate,
    get_job,
    list_job_candidates,
    search_region_candidates,
    start_discovery,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/discovery", tags=["admin-discovery"])


@router.get("/regions/search", response_model=RegionSearchResponse)
def admin_discovery_region_search(
    auth: AdminContext = Depends(admin_required),
    q: str = Query(min_length=2, max_length=200),
    lang: str = Query(default="auto"),
    limit: int = Query(default=5, ge=1, le=20),
) -> RegionSearchResponse:
    _ = lang
    items = search_region_candidates(q, limit=limit)
    return RegionSearchResponse(items=items)


@router.post("/regions/{region_id:path}/discover", response_model=DiscoverRegionResponse)
def admin_discovery_discover_region(
    region_id: str,
    payload: DiscoverRegionRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DiscoverRegionResponse:
    try:
        return start_discovery(db, region_id, payload, actor_id=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def admin_discovery_get_job(
    job_id: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> JobDetailResponse:
    try:
        return get_job(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs/{job_id}/candidates", response_model=CandidateListResponse)
def admin_discovery_list_candidates(
    job_id: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> CandidateListResponse:
    try:
        items = list_job_candidates(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CandidateListResponse(items=items, total=len(items))


@router.get("/candidates/{candidate_id}", response_model=DestinationDiscoveryCandidate)
def admin_discovery_get_candidate(
    candidate_id: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DestinationDiscoveryCandidate:
    try:
        return get_candidate(db, candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/bulk-create", response_model=BulkCreateResult)
def admin_discovery_bulk_create(
    job_id: str,
    payload: BulkCreateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> BulkCreateResult:
    if not payload.candidate_ids:
        raise HTTPException(status_code=422, detail="candidate_ids required")
    return bulk_create_from_job(db, job_id, payload, actor_id=auth.actor_id)
