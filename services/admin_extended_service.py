from __future__ import annotations

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from models.route import Route
from models.route_place import RoutePlace
from schemas.admin import (
    AdminPlaceImageCreateRequest,
    AdminRouteCreateRequest,
    AdminRoutePointsUpdateRequest,
    AdminRouteUpdateRequest,
)
from services.admin_audit_service import write_admin_audit_log
from services.admin_city_import_job_payload import _latest_job, normalize_reviewable_import_state, recover_failed_import_with_places
from services.admin_city_import_tasks import mark_stalled_import_jobs
from services.admin_extra_service import admin_coverage
from services.admin_platform_quality import city_quality_row
from services.place_service import get_place_by_id
from services.route_service import get_route_by_id

PUBLISHABLE_CITY_STATUSES = {
    "review_required",
    "imported",
    "success",
    "success_with_warnings",
    "partial_success",
    "import_failed",
    "unpublished",
}

IMPORT_JOB_LIST_CITY_STATUSES = (
    "importing",
    "imported",
    "review_required",
    "import_failed",
    "published",
)

CityCounters = dict[str, int]


def get_admin_cities(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    _mark_stalled_imports_before_read(db)
    query = db.query(City).order_by(City.updated_at.desc(), City.id.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    city_ids = [city.id for city in cities]
    counters = _city_counters(db, city_ids)
    latest_jobs = _latest_import_jobs(db, city_ids)
    return [
        _city_payload(db, city, counters=counters.get(city.id), latest_job=latest_jobs.get(city.id))
        for city in cities
    ], total


def _city_payload(
    db: Session,
    city: City,
    *,
    counters: CityCounters | None = None,
    latest_job: CityAdminImportJob | None = None,
) -> dict[str, object]:
    if counters is None:
        counters = _city_counters(db, [city.id]).get(city.id, _empty_city_counters())
        latest_job = latest_job or _latest_job(db, city.id)
    places_total = counters["places_total"]
    if latest_job is not None:
        recover_failed_import_with_places(db, city, places_total=places_total, job=latest_job)
        normalize_reviewable_import_state(db, city, latest_job, places_total)
    places_published = counters["places_published"]
    return {
        "id": city.id,
        "slug": city.slug,
        "name": city.name,
        "country": city.country,
        "region": city.region,
        "timezone": city.timezone,
        "center_lat": city.center_lat,
        "center_lng": city.center_lng,
        "launch_status": city.launch_status,
        "is_active": city.is_active,
        "places_total": places_total,
        "places_published": places_published,
        "pending_photos": counters["pending_photos"],
        "can_publish": _can_publish_city(city, places_total),
        "can_unpublish": _can_unpublish_city(city),
    }


def get_admin_import_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    _mark_stalled_imports_before_read(db)
    query = db.query(City).filter(City.launch_status.in_(IMPORT_JOB_LIST_CITY_STATUSES)).order_by(City.updated_at.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    return [_import_job_payload(db, city) for city in cities], total


def list_admin_import_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> dict[str, object]:
    """Compatibility wrapper for routers/admin_import_jobs.py."""
    items, total = get_admin_import_jobs(db, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_admin_import_job(db: Session, city_id: int) -> dict[str, object] | None:
    _mark_stalled_imports_before_read(db)
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None
    return _import_job_payload(db, city)


def get_admin_city_workspace(db: Session, city_slug: str) -> dict[str, object] | None:
    from services.admin_platform_workspace import workspace_operations

    _mark_stalled_imports_before_read(db)
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    city_payload = _city_payload(db, city)
    coverage = _workspace_coverage(db, city.id)
    quality = city_quality_row(db, city)
    return {
        "city": city_payload,
        "readiness": {
            "readiness_score": quality["readiness_score"],
            "stored_readiness_score": quality["stored_readiness_score"],
            "quality_status": city.quality_status,
            "status": city.quality_status,
            "primary_blocker": quality["primary_blocker"],
            "blockers": quality["blockers"],
        },
        "import_job": _import_job_payload(db, city),
        "coverage": coverage,
        "operations": workspace_operations(db, city),
    }


def _workspace_coverage(db: Session, city_id: int) -> dict[str, object] | None:
    coverage = admin_coverage(db, city_id)
    if coverage is None:
        return None
    places = db.query(Place).filter(Place.city_id == city_id)
    return {
        **coverage,
        "total_places": coverage.get("places_total", 0),
        "published_places": coverage.get("places_published", 0),
        "places_without_address": places.filter(Place.address.is_(None)).count(),
    }


def _import_job_payload(db: Session, city: City) -> dict[str, object]:
    from services.admin_city_import_job_payload import build_import_job_payload

    return build_import_job_payload(db, city)


def _mark_stalled_imports_before_read(db: Session) -> None:
    mark_stalled_import_jobs(db, actor_id="admin-panel-read")


def _empty_city_counters() -> CityCounters:
    return {"places_total": 0, "places_published": 0, "pending_photos": 0}


def _city_counters(db: Session, city_ids: list[int]) -> dict[int, CityCounters]:
    counters = {city_id: _empty_city_counters() for city_id in city_ids}
    if not city_ids:
        return counters
    for city_id, places_total, places_published in (
        db.query(
            Place.city_id,
            func.count(Place.id),
            func.sum(case((Place.is_published.is_(True), 1), else_=0)),
        )
        .filter(Place.city_id.in_(city_ids))
        .group_by(Place.city_id)
        .all()
    ):
        counters[int(city_id)]["places_total"] = int(places_total or 0)
        counters[int(city_id)]["places_published"] = int(places_published or 0)
    for city_id, pending_photos in (
        db.query(Place.city_id, func.count(PlaceImage.id))
        .join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id.in_(city_ids), PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
        .group_by(Place.city_id)
        .all()
    ):
        counters[int(city_id)]["pending_photos"] = int(pending_photos or 0)
    return counters


def _latest_import_jobs(db: Session, city_ids: list[int]) -> dict[int, CityAdminImportJob]:
    if not city_ids:
        return {}
    latest_created = (
        db.query(
            CityAdminImportJob.city_id.label("city_id"),
            func.max(CityAdminImportJob.created_at).label("created_at"),
        )
        .filter(CityAdminImportJob.city_id.in_(city_ids))
        .group_by(CityAdminImportJob.city_id)
        .subquery()
    )
    rows = (
        db.query(CityAdminImportJob)
        .join(
            latest_created,
            and_(
                CityAdminImportJob.city_id == latest_created.c.city_id,
                CityAdminImportJob.created_at == latest_created.c.created_at,
            ),
        )
        .order_by(CityAdminImportJob.city_id, CityAdminImportJob.id.desc())
        .all()
    )
    jobs: dict[int, CityAdminImportJob] = {}
    for job in rows:
        jobs[job.city_id] = job
    return jobs


def _can_publish_city(city: City, places_total: int) -> bool:
    return places_total > 0 and city.launch_status in PUBLISHABLE_CITY_STATUSES


def _can_unpublish_city(city: City) -> bool:
    return city.launch_status == "published" and city.is_active


def create_route_from_places(
    db: Session,
    city_id: int,
    title: str,
    place_ids: list[int],
    actor: str = "admin",
) -> Route:
    if len(place_ids) < 2:
        raise ValueError("Для маршрута нужно минимум две точки")
    places = db.query(Place).filter(Place.city_id == city_id, Place.id.in_(place_ids)).all()
    if len(places) != len(set(place_ids)):
        raise ValueError("Не все места найдены в выбранном городе")
    route = Route(city_id=city_id, title=title, status="draft")
    db.add(route)
    db.flush()
    by_id = {place.id: place for place in places}
    for idx, place_id in enumerate(place_ids):
        db.add(RoutePlace(route_id=route.id, place_id=place_id, order_index=idx, visit_duration_min=by_id[place_id].visit_duration_min or 20))
    write_admin_audit_log(db, actor=actor, action="route_created_from_places", entity_type="route", entity_id=str(route.id), new_value={"place_ids": place_ids})
    db.commit()
    db.refresh(route)
    return route


def update_route(
    db: Session,
    route_id: int,
    payload: AdminRouteUpdateRequest,
    actor: str = "admin",
) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"title": route.title, "status": route.status, "duration_min": route.duration_min}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, field, value)
    write_admin_audit_log(db, actor=actor, action="route_updated", entity_type="route", entity_id=str(route.id), old_value=old_value, new_value=payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(route)
    return route


def replace_route_points(
    db: Session,
    route_id: int,
    payload: AdminRoutePointsUpdateRequest,
    actor: str = "admin",
) -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    db.query(RoutePlace).filter(RoutePlace.route_id == route_id).delete()
    for idx, item in enumerate(payload.places):
        place = get_place_by_id(db, item.place_id)
        if place is None:
            raise ValueError(f"Место {item.place_id} не найдено")
        db.add(RoutePlace(route_id=route_id, place_id=item.place_id, order_index=idx, visit_duration_min=item.visit_duration_min))
    write_admin_audit_log(db, actor=actor, action="route_points_replaced", entity_type="route", entity_id=str(route_id), new_value=payload.model_dump())
    db.commit()
    db.refresh(route)
    return route
