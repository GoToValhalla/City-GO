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
    AdminPlaceCreate,
    AdminPlaceImageCreateRequest,
    AdminPlaceImageRead,
    AdminPlaceListResponse,
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
    replace_admin_route_points,
    update_admin_route,
)
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_tasks import run_import_job_background
from services.admin_service import (
    PlacePublicationBlockedError,
    create_admin_place,
    create_city_and_queue_import,
    get_admin_dashboard,
    get_admin_places,
    get_admin_routes,
    publish_place,
    publish_route,
    reject_place,
    unpublish_place,
    unpublish_route,
    update_admin_place,
    verify_place,
)
from services.place_read_service import build_place_read, build_place_reads
from services.route_service import build_route_points
from services.taxonomy_admin_service import list_categories

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


@router.get("/taxonomy/categories")
def read_admin_taxonomy_categories(
    search: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    parent_id: int | None = Query(default=None),
    route_policy: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return list_categories(
        db,
        search=search,
        active=active,
        parent_id=parent_id,
        route_policy=route_policy,
        offset=offset,
        limit=limit,
    )


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
    # create_city_and_queue_import already enqueued exactly one queued row
    # for this brand-new city (queue_city_import_job internally) — this is
    # the only active row it can possibly be, so it is safe to look it up
    # by city_id here rather than changing create_city_and_queue_import's
    # return type just to thread a job_id through.
    job = (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city.id, CityAdminImportJob.status == "queued")
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )
    if job is None:
        raise HTTPException(status_code=500, detail="Задача импорта не была создана")
    background_tasks.add_task(run_import_job_background, city.id, job_id=job.id, actor_id=auth.actor_id)
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
    if result is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return AdminCityPublicationResponse(
        city_id=result.city.id,
        city_slug=result.city.slug,
        city_name=result.city.name,
        launch_status=result.city.launch_status,
        is_active=result.city.is_active,
        places_total=result.places_total,
        places_published=result.places_published,
        places_hidden=result.places_hidden,
        message=f"Город опубликован. На сайт вышло мест: {result.places_published}. Скрыто: {result.places_hidden}.",
    )


@router.post("/cities/{city_id}/unpublish", response_model=AdminCityPublicationResponse)
def unpublish_city_from_admin(
    city_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCityPublicationResponse:
    result = unpublish_city_for_admin(db, city_id, actor=auth.actor_id, reason=payload.reason)
    if result is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return AdminCityPublicationResponse(
        city_id=result.city.id,
        city_slug=result.city.slug,
        city_name=result.city.name,
        launch_status=result.city.launch_status,
        is_active=result.city.is_active,
        places_total=result.places_total,
        places_published=result.places_published,
        places_hidden=result.places_hidden,
        message="Город снят с публикации. Все его места скрыты с сайта и маршрутов.",
    )


@router.get("/cities/{city_id}/coverage", response_model=AdminCoverageResponse)
def read_admin_city_coverage(
    city_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCoverageResponse:
    payload = admin_coverage(db, city_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return AdminCoverageResponse.model_validate(payload)


@router.get("/places", response_model=AdminPlaceListResponse)
def read_admin_places(
    city_slug: str | None = Query(default=None),
    publication_status: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    preset: str | None = Query(default=None),
    has_photo: bool | None = Query(default=None),
    has_address: bool | None = Query(default=None),
    has_description: bool | None = Query(default=None),
    route_eligible: bool | None = Query(default=None),
    low_confidence: bool | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceListResponse:
    items, total = get_admin_places(
        db, city_slug=city_slug, publication_status=publication_status,
        verification_status=verification_status, category=category, q=q, preset=preset,
        has_photo=has_photo, has_address=has_address, has_description=has_description,
        route_eligible=route_eligible, low_confidence=low_confidence, source=source,
        limit=limit, offset=offset,
    )
    return AdminPlaceListResponse(items=build_place_reads(db, items), total=total, limit=limit, offset=offset)


@router.post("/places", response_model=PlaceRead)
def create_place_from_admin(
    payload: AdminPlaceCreate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    # actor из auth context; actor query-param удалён (P0-3)
    return build_place_read(db, create_admin_place(db, payload, actor=auth.actor_id))


@router.put("/places/{place_id}", response_model=PlaceRead)
def update_place_from_admin(
    place_id: int,
    payload: AdminPlaceUpdate,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    # actor из auth context; actor query-param удалён (P0-3)
    place = update_admin_place(db, place_id, payload, actor=auth.actor_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(db, place)


@router.post("/places/{place_id}/publish", response_model=PlaceRead)
def publish_place_from_admin(
    place_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    body = payload or AdminActionRequest()
    try:
        place = publish_place(db, place_id, actor=auth.actor_id, reason=body.reason)
    except PlacePublicationBlockedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "result": "blocked",
                "place_id": exc.place_id,
                "blocked_reason": exc.blocked_reason,
                "failed_gates": exc.failed_gates,
                "message": "Публикация заблокирована: место не прошло проверку безопасности данных (нулевая уверенность и отсутствуют адрес/фото/часы работы).",
            },
        ) from exc
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(db, place)


@router.post("/places/{place_id}/unpublish", response_model=PlaceRead)
def unpublish_place_from_admin(
    place_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    place = unpublish_place(db, place_id, actor=auth.actor_id, reason=payload.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(db, place)


@router.post("/places/{place_id}/reject", response_model=PlaceRead)
def reject_place_from_admin(
    place_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = reject_place(db, place_id, actor=auth.actor_id, reason=payload.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(db, place)


@router.post("/places/{place_id}/verify", response_model=PlaceRead)
def verify_place_from_admin(
    place_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    body = payload or AdminActionRequest()
    place = verify_place(db, place_id, actor=auth.actor_id, reason=body.reason)
    if place is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return build_place_read(db, place)


@router.post("/place-images", response_model=AdminPlaceImageRead)
def create_place_image_from_admin(
    payload: AdminPlaceImageCreateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceImageRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    image = create_admin_place_image(db, payload, actor=auth.actor_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Место не найдено")
    return AdminPlaceImageRead.model_validate(image)


@router.get("/routes", response_model=AdminRouteListResponse)
def read_admin_routes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteListResponse:
    items, total = get_admin_routes(db, limit=limit, offset=offset)
    return AdminRouteListResponse(items=[RouteRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.post("/routes", response_model=RouteRead)
def create_route_from_admin(
    payload: AdminRouteCreateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    return RouteRead.model_validate(create_admin_route(db, payload, actor=auth.actor_id))


@router.put("/routes/{route_id}", response_model=RouteRead)
def update_route_from_admin(
    route_id: int,
    payload: AdminRouteUpdateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    route = update_admin_route(db, route_id, payload, actor=auth.actor_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return RouteRead.model_validate(route)


@router.put("/routes/{route_id}/points", response_model=RouteDetailRead)
def update_route_points_from_admin(
    route_id: int,
    payload: AdminRoutePointsUpdateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteDetailRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    route = replace_admin_route_points(db, route_id, payload, actor=auth.actor_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return RouteDetailRead(
        id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        distance_km=route.distance_km,
        route_mode=route.route_mode,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
        points=build_route_points(route),
    )


@router.post("/routes/{route_id}/publish", response_model=RouteRead)
def publish_route_from_admin(
    route_id: int,
    payload: AdminActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    body = payload or AdminActionRequest()
    route = publish_route(db, route_id, actor=auth.actor_id, reason=body.reason)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return RouteRead.model_validate(route)


@router.post("/routes/{route_id}/unpublish", response_model=RouteRead)
def unpublish_route_from_admin(
    route_id: int,
    payload: AdminUnpublishRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteRead:
    # actor из auth context; payload.actor игнорируется (deprecated)
    route = unpublish_route(db, route_id, actor=auth.actor_id, reason=payload.reason)
    if route is None:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    return RouteRead.model_validate(route)


@router.get("/route-feedback", response_model=AdminRouteFeedbackListResponse)
def read_admin_route_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteFeedbackListResponse:
    items, total = admin_route_feedback(db, limit=limit, offset=offset)
    return AdminRouteFeedbackListResponse(items=[AdminRouteFeedbackRead.model_validate(item) for item in items], total=total, limit=limit, offset=offset)


@router.get("/audit-log", response_model=AdminAuditLogResponse)
def read_admin_audit_log(
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminAuditLogResponse:
    items, total = get_admin_audit_logs(
        db, entity_type=entity_type, action=action, actor=actor, entity_id=entity_id,
        city_slug=city_slug,
        limit=limit, offset=offset,
    )
    applied_filters = {
        "entity_type": entity_type,
        "action": action,
        "actor": actor,
        "entity_id": entity_id,
        "city_slug": city_slug,
    }
    empty_reason = None
    if total == 0:
        active_filters = {key: value for key, value in applied_filters.items() if value}
        empty_reason = (
            f"Нет записей аудита по фильтру: {active_filters}" if active_filters else "Нет записей аудита."
        )
    return AdminAuditLogResponse(
        items=[AdminAuditLogRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        applied_filters=applied_filters,
        empty_reason=empty_reason,
    )