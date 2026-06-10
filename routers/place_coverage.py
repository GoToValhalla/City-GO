from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_coverage import PlaceCoverageReport
from services.place_coverage_service import build_place_coverage_report

router = APIRouter(
    prefix="/place-coverage",
    tags=["place-coverage"],
)


@router.get("/{city_slug}", response_model=PlaceCoverageReport)
def get_place_coverage(
    city_slug: str,
    db: Session = Depends(get_db),
) -> PlaceCoverageReport:
    return build_place_coverage_report(db, city_slug)
