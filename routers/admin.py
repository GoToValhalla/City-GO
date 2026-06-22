from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin import (
    AdminActionRequest,
    AdminAuditLogRead,
    AdminAuditLogResponse,
    AdminCityCreateRequest,
    AdminCityImportResponse,
    AdminCityListResponse,
    AdminCityPublicationResponse,
    AdminCityRead,
    AdminCityWorkspaceResponse,
    AdminDashboardResponse,
    AdminImportJobListResponse,
    AdminImportJobRead,
    AdminPlaceCreate,
    AdminPlaceImageCreateRequest,
    AdminPlaceImageRead,
    AdminPlaceListResponse,
    AdminTaxonomyResponse,
    AdminPlaceUpdate,
    AdminRouteCreateRequest,
    AdminRouteListResponse,
    AdminRoutePointsUpdateRequest,
    AdminRouteUpdateRequest,
    AdminUnpublishRequest,
)
from schemas.admin_extra import (
    AdminCoverageResponse,
    AdminRoleListResponse,
    AdminRoleRead,
    AdminRouteFeedbackListResponse,
    AdminRouteFeedbackRead,
)
from schemas.place import PlaceRead
from schemas.route import RouteDetailRead, RouteRead
from services.admin_audit_service import get_admin_audit_logs
from services.admin_city_publication_service import publish_city as publish_city_for_admin
from services.admin_city_publication_service import unpublish_city as unpublish_city_for_admin
from services.admin_extra_service import ADMIN_ROLES, admin_coverage, admin_route_feedback
from services.admin_extended_service import (
    create_admin_place_image,
    create_admin_route,
    get_admin_cities,
    get_admin_city_workspace,
    get_admin_import_job,
    get_admin_import_jobs,
    replace_admin_route_points,
    update_admin_route,
)
from services.admin_city_import_tasks import run_import_job_background
from services.admin_taxonomy_service import admin_category_taxonomy
from services.admin_service import (
    create_admin_place,
    create_city_and_queue_import,
    get_admin_dashboard,
    get_admin_places,
    get_admin_routes,
    publish_place,
    publish_route,
    unpublish_place,
    unpublish_route,
    update_admin_place,
    verify_place,
)
from services.place_read_service import build_place_read, build_place_reads
from services.route_service import build_route_points

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def read_admin_dashboard(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    return AdminDashboardResponse(**get_admin_dashboard(db))


@router.get("/roles", response_model=AdminRoleListResponse)
def read_admin_roles(auth: AdminContext = Depends(admin_required)) -> AdminRoleListResponse:
    return AdminRoleListResponse(items=[AdminRoleRead.model_validate(role) for role in ADMIN_ROLES])


@router.get("/cities", response_model=AdminCityListResponse)
def read_admin_cities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityListResponse:
    items, total = get_admin_cities(db, limit=limit, offset=offset)
    return AdminCityListResponse(items=[AdminCityRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/taxonomy/categories", response_model=AdminTaxonomyResponse)
def read_admin_taxonomy_categories(
    city_slug: str | None = Query(default=None, min_length=1),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminTaxonomyResponse:
    return AdminTaxonomyResponse(categories=admin_category_taxonomy(db, city_slug=city_slug))


@router.get("/cities/by-slug/{city_slug}/workspace", response_model=AdminCityWorkspaceResponse)
def read_admin_city_workspace(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityWorkspaceResponse:
    payload = get_admin_city_workspace(db, city_slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return AdminCityWorkspaceResponse.model_validate(payload)


@router.post("/cities/import", response_model=AdminCityImportResponse)
def create_city_import(
    payload: AdminCityCreateRequest,
    background_tasks: BackgroundTasks,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityImportResponse:
    # actor берётся из auth context, payload.actor игнорируется (deprecated)
    city = create_city_and_queue_import(db, payload, actor=auth.actor_id)
    background_tasks.add_task(run_import_job_background, city.id, actor_id=auth.actor_id)
    return AdminCityImportResponse(
        city_id=city.id,
        city_slug=city.slug,
        city_name=city.name,
        job_status="queued",
        message="Город создан. Задача на автоматический сбор мест и фото поставлена в очередь.",
        next_step="После завершения импорта проверьте качество данных и опубликуйте город вручную.",
    )


@router.post("/cities/{city_id}/publish", response_model=AdminCityPublicationResponse)
def publish_city_from_admin(
    city_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityPublicationResponse:
    body = payload or AdminActionRequest()
    try:
        result = publish_city_for_admin(db, city_id, actor=auth.actor_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AdminCityPublicationResponse(**result)


@router.post("/cities/{city_id}/unpublish", response_model=AdminCityPublicationResponse)
def unpublish_city_from_admin(
    city_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityPublicationResponse:
    result = unpublish_city_for_admin(db, city_id, actor=auth.actor_id, reason=payload.reason)
    return AdminCityPublicationResponse(**result)


@router.get("/cities/{city_id}/coverage", response_model=AdminCoverageResponse)
def read_admin_city_coverage(
    city_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCoverageResponse:
    return AdminCoverageResponse(**admin_coverage(db, city_id))


@router.post("/cities/{city_id}/images", response_model=AdminPlaceImageRead)
def create_place_image_from_admin(
    city_id: int,
    payload: AdminPlaceImageCreateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceImageRead:
    image = create_admin_place_image(db, payload, actor=auth.actor_id)
    return AdminPlaceImageRead.model_validate(image)


@router.get("/places", response_model=AdminPlaceListResponse)
def read_admin_places(
    city_slug: str | None = None,
    publication_status: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    q: str | None = None,
    preset: str | None = None,
    has_photo: bool | None = None,
    has_address: bool | None = None,
    has_description: bool | None = None,
    route_eligible: bool | None = None,
    low_confidence: bool | None = None,
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceListResponse:
    items, total = get_admin_places(
        db, city_slug=city_slug, publication_status=publication_status, verification_status=verification_status,
        category=category, q=q, preset=preset, has_photo=has_photo, has_address=has_address,
        has_description=has_description, route_eligible=route_eligible, low_confidence=low_confidence, source=source,
        limit=limit, offset=offset,
    )
    return AdminPlaceListResponse(items=build_place_reads(items), total=total, limit=limit, offset=offset)


@router.post("/places", response_model=PlaceRead)
def create_place_from_admin(
    payload: AdminPlaceCreate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = create_admin_place(db, payload, actor=auth.actor_id)
    return build_place_read(place)


@router.patch("/places/{place_id}", response_model=PlaceRead)
def update_place_from_admin(
    place_id: int,
    payload: AdminPlaceUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = update_admin_place(db, place_id, payload, actor=auth.actor_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(place)


@router.post("/places/{place_id}/publish", response_model=PlaceRead)
def publish_place_from_admin(
    place_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    body = payload or AdminActionRequest()
    place = publish_place(db, place_id, actor=auth.actor_id, reason=body.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(place)


@router.post("/places/{place_id}/unpublish", response_model=PlaceRead)
def unpublish_place_from_admin(
    place_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = unpublish_place(db, place_id, actor=auth.actor_id, reason=payload.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(place)


@router.post("/places/{place_id}/verify", response_model=PlaceRead)
def verify_place_from_admin(
    place_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    body = payload or AdminActionRequest()
    place = verify_place(db, place_id, actor=auth.actor_id, reason=body.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(place)


@router.get("/routes", response_model=AdminRouteListResponse)
def read_admin_routes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteListResponse:
    items, total = get_admin_routes(db, limit=limit, offset=offset)
    return AdminRouteListResponse(items=[RouteRead.model_validate(r) for r in items], total=total, limit=limit, offset=offset)


@router.post("/routes", response_model=RouteDetailRead)
def create_route_from_admin(
    payload: AdminRouteCreateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteDetailRead:
    route = create_admin_route(db, payload, actor=auth.actor_id)
    return RouteDetailRead.model_validate(route)


@router.patch("/routes/{route_id}", response_model=RouteDetailRead)
def update_route_from_admin(
    route_id: int,
    payload: AdminRouteUpdateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteDetailRead:
    route = update_admin_route(db, route_id, payload, actor=auth.actor_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return RouteDetailRead.model_validate(route)


@router.put("/routes/{route_id}/points", response_model=AdminRouteActionResponse)
def replace_route_points_from_admin(
    route_id: int,
    payload: AdminRoutePointsUpdateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteActionResponse:
    route = replace_admin_route_points(db, route_id, payload.points, actor=auth.actor_id, reason=payload.reason)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return AdminRouteActionResponse(route=RouteDetailRead.model_validate(route), message="Точки маршрута обновлены")


@router.get("/routes/{route_id}", response_model=RouteDetailRead)
def read_admin_route_detail(
    route_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteDetailRead:
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    build_route_points(route)
    return RouteDetailRead.model_validate(route)


@router.get("/routes/feedback", response_model=AdminRouteFeedbackListResponse)
def read_admin_route_feedback(
    route_id: int | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteFeedbackListResponse:
    items, total = admin_route_feedback(db, route_id=route_id, status=status, limit=limit, offset=offset)
    return AdminRouteFeedbackListResponse(items=[AdminRouteFeedbackRead.model_validate(x) for x in items], total=total, limit=limit, offset=offset)
