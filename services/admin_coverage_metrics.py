"""Метрики покрытия данных по городам и quality score."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_coverage_place_checks import published_quality_counts


def _severity(score: int) -> str:
    if score >= 75:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


def _quality_score(total: int, published: int, with_photo: int, with_addr: int, verified: int) -> int:
    if total <= 0:
        return 0
    pub = published / total
    photo = with_photo / max(published, 1)
    addr = with_addr / max(published, 1)
    ver = verified / max(published, 1)
    return int(round((pub * 0.2 + photo * 0.3 + addr * 0.25 + ver * 0.25) * 100))


def city_coverage_row(db: Session, city: City) -> dict[str, object]:
    places = db.query(Place).filter(Place.city_id == city.id)
    total = places.count()
    published_places = places.filter(Place.is_published.is_(True)).all()
    published = len(published_places)
    hidden = max(total - published, 0)
    verified = places.filter(Place.verification_status == "verified").count()
    unverified = places.filter(Place.verification_status.in_(("unverified", "needs_recheck"))).count()
    with_photo, without_photo, with_addr, without_addr, with_desc, without_desc = published_quality_counts(
        db,
        published_places,
    )
    route_ok = places.filter(Place.is_route_eligible.is_(True)).count()
    route_no = places.filter(Place.is_route_eligible.is_(False)).count()
    pending_photos = (
        db.query(PlaceImage).join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id == city.id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    )
    score = _quality_score(total, published, with_photo, with_addr, verified)
    return {
        "city_id": city.id, "city_slug": city.slug, "city_name": city.name,
        "places_total": total, "places_published": published, "places_hidden": hidden,
        "places_verified": verified, "places_unverified": unverified,
        "places_with_photo": with_photo, "places_without_photo": without_photo,
        "places_with_address": with_addr, "places_without_address": without_addr,
        "places_with_description": with_desc, "places_without_description": without_desc,
        "places_route_eligible": route_ok, "places_not_route_eligible": route_no,
        "pending_photos": pending_photos, "quality_score": score, "severity": _severity(score),
    }


def build_coverage_summary(db: Session, *, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).order_by(City.name.asc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    return [city_coverage_row(db, city) for city in cities], total
