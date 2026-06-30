from __future__ import annotations

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from models.route import Route
from models.route_place import RoutePlace
from schemas.admin import AdminPlaceImageCreateRequest, AdminRouteCreateRequest, AdminRoutePointsUpdateRequest, AdminRouteUpdateRequest
from services.admin_audit_service import write_admin_audit_log
from services.admin_city_import_job_payload import PIPELINE_MODE_LABEL, _latest_job, _snapshot, _snapshot_changes, _snapshot_coverage
from services.admin_extra_service import admin_coverage
from services.admin_platform_quality import city_quality_row
from services.import_pipeline.progress import is_stalled, step_label
from services.import_pipeline.steps import STEP_QUEUED
from services.place_service import get_place_by_id
from services.route_service import get_route_by_id

PUBLISHABLE_CITY_STATUSES = {"review_required", "imported", "success", "success_with_warnings", "partial_success", "import_failed", "unpublished"}
CityCounters = dict[str, int]


def get_admin_cities(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).order_by(City.updated_at.desc(), City.id.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    city_ids = [city.id for city in cities]
    counters = _city_counters(db, city_ids)
    latest_jobs = _latest_import_jobs(db, city_ids)
    return [_city_payload(db, city, counters=counters.get(city.id), latest_job=latest_jobs.get(city.id)) for city in cities], total


def _city_payload(db: Session, city: City, *, counters: CityCounters | None = None, latest_job: CityAdminImportJob | None = None) -> dict[str, object]:
    if counters is None:
        counters = _city_counters(db, [city.id]).get(city.id, _empty_city_counters())
        latest_job = latest_job or _latest_job(db, city.id)
    places_total = counters["places_total"]
    places_published = counters["places_published"]
    return {"id": city.id, "slug": city.slug, "name": city.name, "country": city.country, "region": city.region, "timezone": city.timezone, "center_lat": city.center_lat, "center_lng": city.center_lng, "launch_status": city.launch_status, "is_active": city.is_active, "places_total": places_total, "places_published": places_published, "pending_photos": counters["pending_photos"], "can_publish": _can_publish_city(city, places_total), "can_unpublish": _can_unpublish_city(city)}


def get_admin_import_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).filter(City.launch_status.in_(("importing", "imported", "review_required", "import_failed", "published"))).order_by(City.updated_at.desc(), City.id.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    city_ids = [city.id for city in cities]
    counters = _city_counters(db, city_ids)
    latest_jobs = _latest_import_jobs(db, city_ids)
    return [_import_job_list_payload(city, counters=counters.get(city.id), job=latest_jobs.get(city.id)) for city in cities], total


def list_admin_import_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> dict[str, object]:
    items, total = get_admin_import_jobs(db, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_admin_import_job(db: Session, city_id: int) -> dict[str, object] | None:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None
    return _import_job_payload(db, city)


def get_admin_city_workspace(db: Session, city_slug: str) -> dict[str, object] | None:
    from services.admin_platform_workspace import workspace_operations
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    city_payload = _city_payload(db, city)
    coverage = _workspace_coverage(db, city.id)
    quality = city_quality_row(db, city)
    return {"city": city_payload, "readiness": {"readiness_score": quality["readiness_score"], "stored_readiness_score": quality["stored_readiness_score"], "quality_status": city.quality_status, "status": city.quality_status, "primary_blocker": quality["primary_blocker"], "blockers": quality["blockers"]}, "import_job": _import_job_payload(db, city), "coverage": coverage, "operations": workspace_operations(db, city)}


def _workspace_coverage(db: Session, city_id: int) -> dict[str, object] | None:
    coverage = admin_coverage(db, city_id)
    if coverage is None:
        return None
    places = db.query(Place).filter(Place.city_id == city_id)
    return {**coverage, "total_places": coverage.get("places_total", 0), "published_places": coverage.get("places_published", 0), "places_without_address": places.filter(Place.address.is_(None)).count()}


def _import_job_payload(db: Session, city: City) -> dict[str, object]:
    from services.admin_city_import_job_payload import build_import_job_payload
    return build_import_job_payload(db, city)


def _import_job_list_payload(city: City, *, counters: CityCounters | None, job: CityAdminImportJob | None) -> dict[str, object]:
    counters = counters or _empty_city_counters()
    snapshot = _snapshot(job)
    coverage = _snapshot_coverage(snapshot)
    changes = _snapshot_changes(snapshot)
    city_published = city.launch_status == "published" and bool(city.is_active)
    active_job = job is not None and job.status in {"queued", "running"}
    display_as_published = city_published and not active_job
    raw_status = str(job.status if job is not None else city.launch_status)
    raw_step = str(job.current_step if job is not None else STEP_QUEUED)
    status = "published" if display_as_published else raw_status
    current_step = "published" if display_as_published else raw_step
    places_total = int(coverage.get("places_total") or counters["places_total"])
    places_published = int(coverage.get("places_published") or counters["places_published"])
    is_running = active_job
    step_details = {"admin_pipeline_contract": {"label": PIPELINE_MODE_LABEL}, "data_coverage": coverage, "change_summary": changes, "snapshot_at": snapshot.get("taken_at") if snapshot else None, "snapshot_stale": not bool(snapshot)}
    return {
        "id": f"city-import-{city.id}", "city_id": city.id, "city_slug": city.slug, "city_name": city.name,
        "status": status, "launch_status": city.launch_status, "is_city_active": bool(city.is_active),
        "current_step": current_step, "current_step_label": "Опубликован" if display_as_published else step_label(current_step),
        "source": job.source if job is not None else "admin_city_import", "pipeline_mode": "legacy_osm_plus_foundation", "pipeline_mode_label": PIPELINE_MODE_LABEL,
        "status_group": "published" if display_as_published else ("running" if is_running else "idle"),
        "action_hint": "Город опубликован" if display_as_published else ("Дождаться завершения import-worker" if is_running else "Открыть детали"), "auto_refresh_seconds": 7 if is_running else None,
        "data_coverage": coverage, "change_summary": changes,
        "places_total": places_total, "places_published": places_published, "places_unpublished": max(places_total - places_published, 0), "pending_photos": int(coverage.get("pending_photos") or counters["pending_photos"]),
        "next_step": "Город опубликован и доступен на сайте." if city_published else ("Snapshot готов. Откройте детали для полного отчёта." if snapshot else "Snapshot ещё не создан. Откройте детали и нажмите «Обновить snapshot»."),
        "job_id": job.id if job is not None else None, "scopes_total": job.scopes_total if job is not None else 0, "scopes_succeeded": job.scopes_succeeded if job is not None else 0,
        "places_found": job.places_found if job is not None else 0, "places_saved": job.places_saved if job is not None else 0,
        "total_items": job.total_items if job is not None else 0, "processed_items": job.processed_items if job is not None else 0, "successful_items": job.successful_items if job is not None else 0, "failed_items": job.failed_items if job is not None else 0, "retry_count": job.retry_count if job is not None else 0,
        "step_details": step_details, "is_stalled": False if display_as_published else (is_stalled(job) if job is not None else False),
        "started_at": job.started_at if job is not None else None, "finished_at": job.finished_at if job is not None else None, "created_at": job.created_at if job is not None else None, "updated_at": job.updated_at if job is not None else None,
        "last_error": None if display_as_published else (job.last_error if job is not None and job.status in {"failed", "stalled", "import_failed"} else None),
        "can_run": False, "can_retry": False if active_job else bool(job is not None and job.status in {"failed", "stalled", "import_failed", "success", "success_with_warnings", "partial_success", "cancelled"}),
        "can_cancel": bool(active_job),
        "can_publish": False if active_job or display_as_published else _can_publish_city(city, places_total), "can_unpublish": _can_unpublish_city(city),
        "report_url": f"/admin/routes/data-quality/{city.slug}", "logs_url": f"/admin/system-logs?city_slug={city.slug}&module=import",
    }


def _mark_stalled_imports_before_read(db: Session) -> None:
    return None


def _empty_city_counters() -> CityCounters:
    return {"places_total": 0, "places_published": 0, "pending_photos": 0}


def _city_counters(db: Session, city_ids: list[int]) -> dict[int, CityCounters]:
    counters = {city_id: _empty_city_counters() for city_id in city_ids}
    if not city_ids:
        return counters
    for city_id, places_total, places_published in db.query(Place.city_id, func.count(Place.id), func.sum(case((Place.is_published.is_(True), 1), else_=0))).filter(Place.city_id.in_(city_ids)).group_by(Place.city_id).all():
        counters[int(city_id)]["places_total"] = int(places_total or 0)
        counters[int(city_id)]["places_published"] = int(places_published or 0)
    for city_id, pending_photos in db.query(Place.city_id, func.count(PlaceImage.id)).join(Place, Place.id == PlaceImage.place_id).filter(Place.city_id.in_(city_ids), PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).group_by(Place.city_id).all():
        counters[int(city_id)]["pending_photos"] = int(pending_photos or 0)
    return counters


def _latest_import_jobs(db: Session, city_ids: list[int]) -> dict[int, CityAdminImportJob]:
    if not city_ids:
        return {}
    latest_created = db.query(CityAdminImportJob.city_id.label("city_id"), func.max(CityAdminImportJob.created_at).label("created_at")).filter(CityAdminImportJob.city_id.in_(city_ids)).group_by(CityAdminImportJob.city_id).subquery()
    rows = db.query(CityAdminImportJob).join(latest_created, and_(CityAdminImportJob.city_id == latest_created.c.city_id, CityAdminImportJob.created_at == latest_created.c.created_at)).order_by(CityAdminImportJob.city_id, CityAdminImportJob.id.desc()).all()
    jobs: dict[int, CityAdminImportJob] = {}
    for job in rows:
        jobs.setdefault(int(job.city_id), job)
    return jobs


def _can_publish_city(city: City, places_total: int) -> bool:
    return places_total > 0 and city.launch_status in PUBLISHABLE_CITY_STATUSES and not city.is_active


def _can_unpublish_city(city: City) -> bool:
    return city.launch_status == "published" and bool(city.is_active)


def create_admin_route(db: Session, payload: AdminRouteCreateRequest, *, actor: str = "admin") -> Route:
    route = Route(city_id=payload.city_id, slug=payload.slug, title=payload.title, short_description=payload.short_description, duration_minutes=payload.duration_minutes, distance_km=payload.distance_km, route_mode=payload.route_mode, is_active=payload.is_active)
    db.add(route); db.flush(); write_admin_audit_log(db, actor=actor, action="create_route", entity_type="route", entity_id=route.id, new_value={"title": route.title, "is_active": route.is_active}); db.commit(); db.refresh(route); return route


def update_admin_route(db: Session, route_id: int, payload: AdminRouteUpdateRequest, *, actor: str = "admin") -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"title": route.title, "is_active": route.is_active, "route_mode": route.route_mode}
    for field in ("slug", "title", "short_description", "duration_minutes", "distance_km", "route_mode", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(route, field, value)
    write_admin_audit_log(db, actor=actor, action="update_route", entity_type="route", entity_id=route.id, old_value=old_value, new_value={"title": route.title, "is_active": route.is_active, "route_mode": route.route_mode})
    db.commit(); db.refresh(route); return route


def replace_admin_route_points(db: Session, route_id: int, payload: AdminRoutePointsUpdateRequest, *, actor: str = "admin") -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"points": [{"place_id": item.place_id, "position": item.position} for item in route.route_places]}
    for current_point in list(route.route_places):
        db.delete(current_point)
    for point in sorted(payload.points, key=lambda item: item.position):
        db.add(RoutePlace(route_id=route_id, place_id=point.place_id, position=point.position))
    write_admin_audit_log(db, actor=actor, action="replace_route_points", entity_type="route", entity_id=route_id, old_value=old_value, new_value={"points": [item.model_dump() for item in payload.points]}, reason=payload.reason)
    db.commit(); return get_route_by_id(db, route_id)


def create_admin_place_image(db: Session, payload: AdminPlaceImageCreateRequest, *, actor: str = "admin") -> PlaceImage | None:
    place = get_place_by_id(db, payload.place_id)
    if place is None:
        return None
    image = PlaceImage(place_id=payload.place_id, image_url=payload.image_url, thumbnail_url=payload.thumbnail_url, source_type=payload.source_type, source_url=payload.source_url, attribution=payload.attribution, license=payload.license, confidence=payload.confidence, status=PLACE_IMAGE_STATUS_NEEDS_REVIEW)
    db.add(image); write_admin_audit_log(db, actor=actor, action="create_place_image", entity_type="place_image", entity_id=None, new_value={"place_id": payload.place_id, "image_url": payload.image_url, "source_type": payload.source_type}, reason=payload.comment); db.commit(); db.refresh(image); return image
