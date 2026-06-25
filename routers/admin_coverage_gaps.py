from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.coverage_gap_service import build_coverage_summary

router = APIRouter(prefix="/admin/coverage-gaps", tags=["admin-coverage-gaps"])


@router.get("")
def list_coverage_gaps(
    city_slug: str | None = None,
    status: str | None = None,
    gap_reason: str | None = None,
    expected_category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
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
    )


@router.get("/cities/{city_slug}")
def get_city_coverage_gaps(
    city_slug: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=300),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return build_coverage_summary(db, city_slug=city_slug, offset=offset, limit=limit)
