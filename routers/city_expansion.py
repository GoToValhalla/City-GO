from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.city_expansion import (
    CityCandidateCreate,
    CityCandidateRead,
    CountryCreate,
    CountryRead,
    ImportCoverageReport,
    ImportScopeCreate,
    ImportScopeRead,
    RegionCreate,
    RegionRead,
)
from services.city_registry_service import (
    create_city_candidate,
    create_country,
    create_import_scope,
    create_region,
    list_city_candidates,
    list_countries,
    list_import_scopes,
    list_regions,
)
from services.import_coverage_service import build_import_coverage_report

router = APIRouter(prefix="/city-expansion", tags=["city-expansion"])


@router.get("/countries", response_model=list[CountryRead])
def countries(db: Session = Depends(get_db)) -> list[CountryRead]:
    return list_countries(db)


@router.post("/countries", response_model=CountryRead)
def post_country(payload: CountryCreate, db: Session = Depends(get_db)) -> CountryRead:
    return create_country(db, payload)


@router.get("/regions", response_model=list[RegionRead])
def regions(db: Session = Depends(get_db)) -> list[RegionRead]:
    return list_regions(db)


@router.post("/regions", response_model=RegionRead)
def post_region(payload: RegionCreate, db: Session = Depends(get_db)) -> RegionRead:
    return create_region(db, payload)


@router.get("/city-candidates", response_model=list[CityCandidateRead])
def city_candidates(db: Session = Depends(get_db)) -> list[CityCandidateRead]:
    return list_city_candidates(db)


@router.post("/city-candidates", response_model=CityCandidateRead)
def post_candidate(payload: CityCandidateCreate, db: Session = Depends(get_db)) -> CityCandidateRead:
    return create_city_candidate(db, payload)


@router.get("/scopes", response_model=list[ImportScopeRead])
def scopes(city_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> list[ImportScopeRead]:
    return list_import_scopes(db, city_id)


@router.post("/scopes", response_model=ImportScopeRead)
def post_scope(payload: ImportScopeCreate, db: Session = Depends(get_db)) -> ImportScopeRead:
    return create_import_scope(db, payload)


@router.get("/coverage/{city_slug}", response_model=ImportCoverageReport)
def import_coverage(
    city_slug: str,
    scope_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ImportCoverageReport:
    return build_import_coverage_report(db, city_slug, scope_code)
