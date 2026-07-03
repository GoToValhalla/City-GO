"""Метрики покрытия данных по городам и quality score."""

from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from services.admin_coverage_place_checks import place_has_coverage_address, place_has_coverage_description
from services.place_public_image_service import resolve_public_place_images_bulk


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
    metrics = _place_metrics(db, [city.id]).get(city.id, _empty_metrics())
    pending = _pending_photo_counts(db, [city.id]).get(city.id, 0)
    metrics.update(_published_quality_by_city(db, [city.id]).get(city.id, {}))
    return _row(city, metrics, pending)


def _row(city: City, metrics: dict[str, int], pending_photos: int) -> dict[str, object]:
    total = metrics["total"]
    published = metrics["published"]
    hidden = max(total - published, 0)
    verified = metrics["verified"]
    unverified = metrics["unverified"]
    with_photo = metrics["with_photo"]
    without_photo = max(published - with_photo, 0)
    with_addr = metrics["with_addr"]
    without_addr = max(published - with_addr, 0)
    with_desc = metrics["with_desc"]
    without_desc = max(published - with_desc, 0)
    route_ok = metrics["route_ok"]
    route_no = metrics["route_no"]
    route_unknown = metrics["route_unknown"]
    score = _quality_score(total, published, with_photo, with_addr, verified)
    return {
        "city_id": city.id, "city_slug": city.slug, "city_name": city.name,
        "places_total": total, "places_published": published, "places_hidden": hidden,
        "places_verified": verified, "places_unverified": unverified,
        "places_with_photo": with_photo, "places_without_photo": without_photo,
        "places_with_address": with_addr, "places_without_address": without_addr,
        "places_with_description": with_desc, "places_without_description": without_desc,
        "places_route_eligible": route_ok, "places_not_route_eligible": route_no, "places_route_unknown": route_unknown,
        "pending_photos": pending_photos, "quality_score": score, "severity": _severity(score),
    }


def build_coverage_summary(db: Session, *, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, object]], int]:
    query = db.query(City).order_by(City.name.asc())
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    city_ids = [int(city.id) for city in cities]
    metrics = _place_metrics(db, city_ids)
    quality = _published_quality_by_city(db, city_ids)
    pending = _pending_photo_counts(db, city_ids)
    rows = []
    for city in cities:
        city_metrics = metrics.get(city.id, _empty_metrics())
        city_metrics.update(quality.get(city.id, {}))
        rows.append(_row(city, city_metrics, pending.get(city.id, 0)))
    return rows, total


def _place_metrics(db: Session, city_ids: list[int]) -> dict[int, dict[str, int]]:
    if not city_ids:
        return {}
    rows = db.query(
        Place.city_id,
        func.count(Place.id).label("total"),
        _sum(Place.is_published.is_(True)).label("published"),
        _sum(Place.verification_status == "verified").label("verified"),
        _sum(Place.verification_status.in_(("unverified", "needs_recheck"))).label("unverified"),
        _sum(Place.is_route_eligible.is_(True)).label("route_ok"),
        _sum(Place.is_route_eligible.is_not(True)).label("route_no"),
        _sum(Place.is_route_eligible.is_(None)).label("route_unknown"),
    ).filter(Place.city_id.in_(city_ids)).group_by(Place.city_id).all()
    return {int(row.city_id): {key: int(getattr(row, key) or 0) for key in _PLACE_METRIC_KEYS} for row in rows}


def _pending_photo_counts(db: Session, city_ids: list[int]) -> dict[int, int]:
    if not city_ids:
        return {}
    rows = (
        db.query(Place.city_id, func.count(PlaceImage.id))
        .join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id.in_(city_ids), PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
        .group_by(Place.city_id)
        .all()
    )
    return {int(city_id): int(count or 0) for city_id, count in rows}


def _published_quality_by_city(db: Session, city_ids: list[int]) -> dict[int, dict[str, int]]:
    if not city_ids:
        return {}
    places = db.query(Place).filter(Place.city_id.in_(city_ids), Place.is_published.is_(True)).all()
    public_images = resolve_public_place_images_bulk(db, places, limit_per_place=1)
    result: dict[int, dict[str, int]] = {}
    for place in places:
        bucket = result.setdefault(int(place.city_id), {"with_photo": 0, "with_addr": 0, "with_desc": 0})
        bucket["with_photo"] += 1 if public_images.get(place.id) else 0
        bucket["with_addr"] += 1 if place_has_coverage_address(place) else 0
        bucket["with_desc"] += 1 if place_has_coverage_description(place) else 0
    return result


def _sum(*conditions):
    return func.sum(case((conditions[0] if len(conditions) == 1 else _and(*conditions), 1), else_=0))


def _and(*conditions):
    from sqlalchemy import and_

    return and_(*conditions)


_METRIC_KEYS = ("total", "published", "verified", "unverified", "with_photo", "with_addr", "with_desc", "route_ok", "route_no", "route_unknown")
_PLACE_METRIC_KEYS = ("total", "published", "verified", "unverified", "route_ok", "route_no", "route_unknown")


def _empty_metrics() -> dict[str, int]:
    return {key: 0 for key in _METRIC_KEYS}
