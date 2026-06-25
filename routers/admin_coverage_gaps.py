from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.coverage_gap_admin_actions import coverage_gap_row_payload, update_coverage_gap_status
from services.coverage_gap_service import (
    CRITICAL_POLICIES,
    UNRESOLVED_STATUSES,
    build_coverage_summary,
    refresh_coverage_statuses,
    sync_known_missing_poi_seed,
)

router = APIRouter(prefix="/admin/coverage-gaps", tags=["admin-coverage-gaps"])
VIRTUAL_STATUS_FILTERS = {"unresolved", "critical"}


class CoverageGapUpdateRequest(BaseModel):
    status: str | None = None
    gap_reason: str | None = None
    matched_place_id: int | None = None
    review_notes: str | None = None


@router.get("")
def list_coverage_gaps(
    city_slug: str | None = None,
    status: str | None = None,
    gap_reason: str | None = None,
    expected_category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    refresh: bool = True,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    virtual_status = status if status in VIRTUAL_STATUS_FILTERS else None
    payload = build_coverage_summary(
        db,
        city_slug=city_slug,
        status=None if virtual_status else status,
        gap_reason=gap_reason,
        expected_category=expected_category,
        offset=0 if virtual_status else offset,
        limit=300 if virtual_status else limit,
        refresh=refresh,
    )
    if virtual_status:
        payload = _apply_virtual_status_filter(payload, virtual_status, offset=offset, limit=limit)
    return payload


@router.get("/cities/{city_slug}")
def get_city_coverage_gaps(
    city_slug: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    refresh: bool = True,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return build_coverage_summary(db, city_slug=city_slug, offset=offset, limit=limit, refresh=refresh)


@router.post("/sync")
def sync_coverage_gaps(
    city_slug: str | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = sync_known_missing_poi_seed(db, city_slug=city_slug)
    db.commit()
    return {"status": "success", "synced": result}


@router.post("/refresh")
def refresh_coverage_gaps(
    city_slug: str | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = refresh_coverage_statuses(db, city_slug=city_slug)
    db.commit()
    return {"status": "success", **result}


@router.patch("/{gap_id}")
def patch_coverage_gap(
    gap_id: int,
    body: CoverageGapUpdateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        row = update_coverage_gap_status(
            db,
            gap_id=gap_id,
            status=body.status,
            gap_reason=body.gap_reason,
            matched_place_id=body.matched_place_id,
            review_notes=body.review_notes,
            actor_id=auth.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="Coverage gap not found")
    db.commit()
    db.refresh(row)
    return {"status": "success", "item": coverage_gap_row_payload(row)}


def _apply_virtual_status_filter(payload: dict[str, Any], status: str, *, offset: int, limit: int) -> dict[str, Any]:
    """Applies UI helper filters that are not persisted as real row statuses."""

    rows = [item for item in payload.get("items", []) if isinstance(item, dict)]
    if status == "unresolved":
        rows = [item for item in rows if item.get("status") in UNRESOLVED_STATUSES]
    elif status == "critical":
        rows = [
            item for item in rows
            if item.get("expected_route_policy") in CRITICAL_POLICIES
            and item.get("status") in UNRESOLVED_STATUSES
        ]
    else:
        return payload

    paged = rows[offset: offset + limit]
    return {
        **payload,
        "items": paged,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "filters": {**dict(payload.get("filters") or {}), "status": status},
    }
