from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.coverage_gap_admin_actions import coverage_gap_row_payload, update_coverage_gap_status
from services.coverage_gap_service import build_coverage_summary, refresh_coverage_statuses, sync_known_missing_poi_seed

router = APIRouter(prefix="/admin/coverage-gaps", tags=["admin-coverage-gaps"])


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
    return build_coverage_summary(
        db,
        city_slug=city_slug,
        status=status,
        gap_reason=gap_reason,
        expected_category=expected_category,
        offset=offset,
        limit=limit,
        refresh=refresh,
    )


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
