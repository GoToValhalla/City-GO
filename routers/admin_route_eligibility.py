"""Admin: eligibility list, data quality, city readiness."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from models.place import Place
from schemas.admin_route_operations import (
    CityReadinessListResponse,
    CityReadinessResponse,
    DataQualityReport,
    EligibilityListResponse,
    EligibilityPlaceRow,
    RouteReadinessDiagnosticsResponse,
)
from services.admin_audit_service import write_admin_audit_log
from services.city_readiness import (
    compute_city_readiness,
    list_cities_readiness,
    recalculate_city_readiness_snapshot,
)
from services.route_data_quality import build_route_data_quality_report
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES
from services.route_eligibility_dashboard import build_route_readiness_diagnostics, list_eligibility_places

router = APIRouter(prefix="/admin/routes", tags=["admin-routes"])


@router.get("/eligibility", response_model=EligibilityListResponse)
def get_route_eligibility(
    city_slug: str | None = Query(default=None),
    category: str | None = Query(default=None),
    eligible: bool | None = Query(default=None),
    no_photo: bool | None = Query(default=None),
    no_address: bool | None = Query(default=None),
    no_description: bool | None = Query(default=None),
    unpublished: bool | None = Query(default=None),
    inactive: bool | None = Query(default=None),
    issue: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> EligibilityListResponse:
    items, total = list_eligibility_places(
        db, city_slug=city_slug, category=category, eligible=eligible,
        no_photo=no_photo, no_address=no_address, no_description=no_description,
        unpublished=unpublished, inactive=inactive, issue=issue, limit=limit, offset=offset,
    )
    return EligibilityListResponse(
        items=[EligibilityPlaceRow.model_validate(row) for row in items],
        total=total, limit=limit, offset=offset,
    )


@router.get("/eligibility/{city_slug}", response_model=RouteReadinessDiagnosticsResponse)
def get_route_readiness_diagnostics(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteReadinessDiagnosticsResponse:
    payload = build_route_readiness_diagnostics(db, city_slug)
    if payload is None:
        raise HTTPException(404, "Город не найден")
    return RouteReadinessDiagnosticsResponse.model_validate(payload)


@router.get("/data-quality/{city_slug}", response_model=DataQualityReport)
def get_route_data_quality(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DataQualityReport:
    payload = build_route_data_quality_report(db, city_slug=city_slug)
    if payload is None:
        raise HTTPException(404, "Город не найден")
    return DataQualityReport.model_validate(payload)


@router.post("/data-quality/{city_slug}/exclude-forbidden-categories")
def exclude_forbidden_route_categories(
    city_slug: str,
    body: dict[str, object],
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if body.get("confirm") is not True:
        raise HTTPException(422, "Требуется confirm=true")

    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise HTTPException(404, "Город не найден")

    places = db.query(Place).filter(
        Place.city_id == city.id,
        Place.category.in_(tuple(ROUTE_FORBIDDEN_CATEGORIES)),
        Place.is_route_eligible.is_(True),
    ).all()

    for place in places:
        place.is_route_eligible = False
        place.route_exclusion_reason = "forbidden_category_cleanup"

    write_admin_audit_log(
        db,
        actor=auth.actor_id,
        action="exclude_forbidden_route_categories",
        entity_type="city",
        entity_id=city.slug,
        old_value=None,
        new_value={"affected": len(places)},
        reason="data_quality_action",
    )
    db.commit()

    return {
        "city_slug": city.slug,
        "affected": len(places),
        "status": "done",
        "reason": "forbidden_category_cleanup",
    }


@router.get("/readiness", response_model=CityReadinessListResponse)
def list_city_readiness(
    limit: int = Query(default=100, ge=1, le=200),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> CityReadinessListResponse:
    items = list_cities_readiness(db, limit=limit)
    return CityReadinessListResponse(
        items=[CityReadinessResponse.model_validate(row) for row in items],
    )


@router.post("/readiness/{city_slug}/recalculate")
def recalculate_city_readiness(
    city_slug: str,
    body: dict[str, object] | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    body = body or {}
    payload = recalculate_city_readiness_snapshot(
        db,
        city_slug=city_slug,
        reason=str(body.get("reason") or "admin_city_readiness_recalculation"),
        recalculate_place_scores=body.get("recalculate_place_scores") is not False,
    )
    if payload is None:
        raise HTTPException(404, "Город не найден")
    write_admin_audit_log(
        db,
        actor=auth.actor_id,
        action="recalculate_city_readiness",
        entity_type="city",
        entity_id=city_slug,
        old_value=None,
        new_value={
            "readiness_score": payload["readiness_score"],
            "status": payload["status"],
            "snapshot_id": payload.get("snapshot_id"),
        },
        reason="data_foundation_action",
    )
    db.commit()
    return payload


@router.get("/readiness/{city_slug}", response_model=CityReadinessResponse)
def get_city_readiness(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> CityReadinessResponse:
    payload = compute_city_readiness(db, city_slug=city_slug)
    if payload is None:
        raise HTTPException(404, "Город не найден")
    return CityReadinessResponse.model_validate(payload)
