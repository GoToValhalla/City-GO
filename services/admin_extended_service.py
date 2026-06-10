from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
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
from services.place_service import get_place_by_id
from services.route_service import get_route_by_id


def get_admin_cities(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).order_by(City.updated_at.desc(), City.id.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    return [_city_payload(db, city) for city in cities], total


def _city_payload(db: Session, city: City) -> dict[str, object]:
    places_query = db.query(Place).filter(Place.city_id == city.id)
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
        "places_total": places_query.count(),
        "places_published": places_query.filter(Place.is_published.is_(True)).count(),
        "pending_photos": (
            db.query(PlaceImage)
            .join(Place, Place.id == PlaceImage.place_id)
            .filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
            .count()
        ),
    }


def get_admin_import_jobs(db: Session, *, limit: int = 50, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).filter(
        City.launch_status.in_(("importing", "imported", "review_required", "import_failed"))
    ).order_by(City.updated_at.desc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    return [_import_job_payload(db, city) for city in cities], total


def get_admin_import_job(db: Session, city_id: int) -> dict[str, object] | None:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None
    return _import_job_payload(db, city)


def _import_job_payload(db: Session, city: City) -> dict[str, object]:
    from services.admin_city_import_job_payload import build_import_job_payload

    return build_import_job_payload(db, city)


def create_admin_route(db: Session, payload: AdminRouteCreateRequest, *, actor: str = "admin") -> Route:
    route = Route(
        city_id=payload.city_id,
        slug=payload.slug,
        title=payload.title,
        short_description=payload.short_description,
        duration_minutes=payload.duration_minutes,
        distance_km=payload.distance_km,
        route_mode=payload.route_mode,
        is_active=payload.is_active,
    )
    db.add(route)
    db.flush()
    # payload.actor игнорируется — используем actor из auth context (P0-3)
    write_admin_audit_log(
        db,
        actor=actor,
        action="create_route",
        entity_type="route",
        entity_id=route.id,
        new_value={"title": route.title, "is_active": route.is_active},
    )
    db.commit()
    db.refresh(route)
    return route


def update_admin_route(db: Session, route_id: int, payload: AdminRouteUpdateRequest, *, actor: str = "admin") -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"title": route.title, "is_active": route.is_active, "route_mode": route.route_mode}
    for field in ("slug", "title", "short_description", "duration_minutes", "distance_km", "route_mode", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(route, field, value)
    # payload.actor игнорируется — используем actor из auth context (P0-3)
    write_admin_audit_log(
        db,
        actor=actor,
        action="update_route",
        entity_type="route",
        entity_id=route.id,
        old_value=old_value,
        new_value={"title": route.title, "is_active": route.is_active, "route_mode": route.route_mode},
    )
    db.commit()
    db.refresh(route)
    return route


def replace_admin_route_points(db: Session, route_id: int, payload: AdminRoutePointsUpdateRequest, *, actor: str = "admin") -> Route | None:
    route = get_route_by_id(db, route_id)
    if route is None:
        return None
    old_value = {"points": [{"place_id": item.place_id, "position": item.position} for item in route.route_places]}
    for current_point in list(route.route_places):
        db.delete(current_point)
    for point in sorted(payload.points, key=lambda item: item.position):
        db.add(RoutePlace(route_id=route_id, place_id=point.place_id, position=point.position))
    # payload.actor игнорируется — используем actor из auth context (P0-3)
    write_admin_audit_log(
        db,
        actor=actor,
        action="replace_route_points",
        entity_type="route",
        entity_id=route_id,
        old_value=old_value,
        new_value={"points": [item.model_dump() for item in payload.points]},
        reason=payload.reason,
    )
    db.commit()
    return get_route_by_id(db, route_id)


def create_admin_place_image(db: Session, payload: AdminPlaceImageCreateRequest, *, actor: str = "admin") -> PlaceImage | None:
    place = get_place_by_id(db, payload.place_id)
    if place is None:
        return None
    image = PlaceImage(
        place_id=payload.place_id,
        image_url=payload.image_url,
        thumbnail_url=payload.thumbnail_url,
        source_type=payload.source_type,
        source_url=payload.source_url,
        attribution=payload.attribution,
        license=payload.license,
        confidence=payload.confidence,
        status=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
        review_comment=payload.comment,
    )
    db.add(image)
    db.flush()
    # payload.actor игнорируется — используем actor из auth context (P0-3)
    write_admin_audit_log(
        db,
        actor=actor,
        action="create_place_image",
        entity_type="place_image",
        entity_id=image.id,
        new_value={"place_id": image.place_id, "image_url": image.image_url, "status": image.status},
        reason=payload.comment,
    )
    db.commit()
    db.refresh(image)
    return image
