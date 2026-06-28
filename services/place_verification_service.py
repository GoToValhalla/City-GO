from __future__ import annotations

import math
from datetime import datetime
from functools import reduce
from typing import Any

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.place import Place
from models.place_verification import PlaceVerification
from models.place_verification_task import PlaceVerificationTask
from schemas.place_verification import PlaceVerificationEnqueueSummary
from services.place_staleness_policy import is_needs_verification


CONFIDENCE_LEVELS = (
    (95, "verified"),
    (80, "high"),
    (60, "medium"),
    (30, "low"),
    (0, "unknown"),
)


def confidence_level(score: int) -> str:
    for threshold, level in CONFIDENCE_LEVELS:
        if score >= threshold:
            return level
    return "unknown"


def enqueue_stale_places(db: Session, city_slug: str) -> PlaceVerificationEnqueueSummary:
    places = db.query(Place).join(City).filter(City.slug == city_slug).all()
    state = reduce(lambda acc, place: _enqueue_if_stale(db, acc, place), places, (0, 0))
    db.commit()
    return PlaceVerificationEnqueueSummary(
        city_slug=city_slug,
        enqueued=state[0],
        already_pending=state[1],
    )


def pending_verification_tasks(db: Session, limit: int = 100) -> list[PlaceVerificationTask]:
    return (
        db.query(PlaceVerificationTask)
        .filter(PlaceVerificationTask.status == "pending")
        .order_by(PlaceVerificationTask.priority.desc(), PlaceVerificationTask.created_at.asc())
        .limit(limit)
        .all()
    )


def get_place_verification_queue(
    db: Session,
    *,
    city_slug: str | None = None,
    status: str | None = None,
    confidence_level_filter: str | None = None,
    max_confidence: int | None = None,
    category: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_meters: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    query = _verification_base_query(db)

    if city_slug:
        query = query.filter(City.slug == city_slug)
    if status:
        query = query.filter(Place.verification_status == status)
    if confidence_level_filter:
        query = query.filter(Place.existence_confidence_level == confidence_level_filter)
    if max_confidence is not None:
        query = query.filter(Place.existence_confidence_score <= max_confidence)
    if category:
        query = query.filter(Place.category == category)

    if radius_meters is not None and lat is not None and lng is not None:
        return _distance_filtered_queue(query, lat=lat, lng=lng, radius_meters=radius_meters, limit=limit, offset=offset)

    total = query.count()
    rows = (
        query.options(joinedload(Place.city))
        .order_by(
            case((Place.verification_status == "needs_recheck", 0), else_=1),
            func.coalesce(Place.existence_confidence_score, 0).asc(),
            Place.id.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_place_queue_payload(place, lat=lat, lng=lng) for place in rows], total


def apply_place_verification(
    db: Session,
    place_id: int,
    *,
    action: str,
    verifier: str | None = None,
    verifier_lat: float | None = None,
    verifier_lng: float | None = None,
    photo_url: str | None = None,
    comment: str | None = None,
) -> Place:
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise LookupError(f"Place {place_id} not found")

    distance = None
    if verifier_lat is not None and verifier_lng is not None:
        distance = _distance_meters(place.lat, place.lng, verifier_lat, verifier_lng)

    score_before = int(place.existence_confidence_score or 0)
    level_before = place.existence_confidence_level or confidence_level(score_before)

    now = datetime.utcnow()
    source = "field_visit" if verifier_lat is not None and verifier_lng is not None else "manual_admin"
    method = "manual_override"
    score_after = score_before
    status_after = place.verification_status or "unverified"
    is_active = place.is_active
    place_status = place.status

    if action == "exists":
        status_after = "verified"
        score_after = 100
        method = "onsite_confirmed" if distance is not None else "manual_override"
        is_active = True
        if place_status in {"draft", "needs_review"}:
            place_status = "active"
    elif action == "not_found":
        status_after = "not_found"
        score_after = 15
        method = "onsite_confirmed" if distance is not None else "manual_override"
        is_active = False
        place_status = "needs_review"
    elif action == "closed":
        status_after = "closed"
        score_after = 0
        method = "onsite_confirmed" if distance is not None else "manual_override"
        is_active = False
        place_status = "closed"
    elif action == "moved":
        status_after = "moved"
        score_after = 40
        method = "onsite_confirmed" if distance is not None else "manual_override"
        is_active = False
        place_status = "needs_review"
    elif action == "duplicate":
        status_after = "duplicate"
        score_after = 0
        method = "manual_override"
        is_active = False
        place_status = "rejected"
    elif action == "needs_recheck":
        status_after = "needs_recheck"
        score_after = min(score_before, 50)
        method = "manual_override"
    else:
        raise ValueError(f"Unsupported verification action: {action}")

    level_after = confidence_level(score_after)

    place.existence_confidence_score = score_after
    place.existence_confidence_level = level_after
    place.verification_status = status_after
    place.verification_source = source
    place.verification_method = method
    place.verified_at = now if action in {"exists", "not_found", "closed", "moved", "duplicate"} else place.verified_at
    place.verified_by = verifier or "local_admin"
    place.verification_comment = comment
    place.is_active = is_active
    place.status = place_status
    place.last_verified_at = now
    place.updated_at = now

    db.add(
        PlaceVerification(
            place_id=place.id,
            status=status_after,
            confidence_score_before=score_before,
            confidence_score_after=score_after,
            confidence_level_before=level_before,
            confidence_level_after=level_after,
            verification_source=source,
            verification_method=method,
            verifier=verifier or "local_admin",
            verifier_lat=verifier_lat,
            verifier_lng=verifier_lng,
            distance_to_place_meters=distance,
            photo_url=photo_url,
            comment=comment,
            created_at=now,
        )
    )

    db.commit()
    db.refresh(place)
    return place


def confirm_place_nearby(
    db: Session,
    place_id: int,
    *,
    verifier: str | None,
    verifier_lat: float,
    verifier_lng: float,
    comment: str | None = None,
    max_distance_meters: float = 150,
) -> Place:
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise LookupError(f"Place {place_id} not found")

    distance = _distance_meters(place.lat, place.lng, verifier_lat, verifier_lng)
    if distance > max_distance_meters:
        raise ValueError(f"Too far from place: {round(distance)}m")

    return apply_place_verification(
        db,
        place_id,
        action="exists",
        verifier=verifier or "local_admin",
        verifier_lat=verifier_lat,
        verifier_lng=verifier_lng,
        comment=comment,
    )


def place_verification_stats(db: Session, city_slug: str) -> dict[str, Any]:
    rows = db.query(Place).join(City, City.id == Place.city_id).filter(City.slug == city_slug).all()
    total = len(rows)
    categories: dict[str, dict[str, int]] = {}

    def inc(category_name: str, bucket: str) -> None:
        categories.setdefault(category_name, {"total": 0, "verified": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0})
        categories[category_name]["total"] += 1
        categories[category_name][bucket] += 1

    verified = high = medium = low = unknown = needs_recheck = closed = not_found = 0
    for place in rows:
        level = place.existence_confidence_level or "unknown"
        status = place.verification_status or "unverified"
        category_name = place.category or "unknown"

        if status == "verified":
            verified += 1
        if level == "high":
            high += 1
        elif level == "medium":
            medium += 1
        elif level == "low":
            low += 1
        else:
            unknown += 1
        if status == "needs_recheck":
            needs_recheck += 1
        if status == "closed":
            closed += 1
        if status == "not_found":
            not_found += 1

        bucket = level if level in {"high", "medium", "low"} else "unknown"
        if status == "verified":
            bucket = "verified"
        inc(category_name, bucket)

    return {
        "city_slug": city_slug,
        "total_places": total,
        "verified_count": verified,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "unknown_count": unknown,
        "needs_recheck_count": needs_recheck,
        "closed_count": closed,
        "not_found_count": not_found,
        "verified_percent": round((verified / total) * 100, 2) if total else 0.0,
        "categories": categories,
    }


def place_verification_summary(db: Session, city_slug: str | None = None) -> dict[str, int]:
    query = db.query(Place)
    if city_slug:
        query = query.join(City, City.id == Place.city_id).filter(City.slug == city_slug)

    queue_filter = or_(
        Place.verification_status.in_(("needs_recheck", "unverified")),
        Place.verification_status.is_(None),
    )
    unverified_filter = or_(
        Place.verification_status == "unverified",
        Place.verification_status.is_(None),
    )
    low_confidence_filter = or_(
        Place.existence_confidence_level.in_(("low", "unknown")),
        Place.existence_confidence_level.is_(None),
    )
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    row = query.with_entities(
        func.sum(case((queue_filter, 1), else_=0)).label("queue_total"),
        func.sum(case((Place.verification_status == "needs_recheck", 1), else_=0)).label("needs_recheck"),
        func.sum(case((unverified_filter, 1), else_=0)).label("unverified"),
        func.sum(case((low_confidence_filter, 1), else_=0)).label("low_confidence"),
        func.sum(case((and_(Place.verification_status == "verified", Place.verified_at >= today_start), 1), else_=0)).label("verified_today"),
    ).one()

    return {
        "queue_total": int(row.queue_total or 0),
        "needs_recheck": int(row.needs_recheck or 0),
        "unverified": int(row.unverified or 0),
        "low_confidence": int(row.low_confidence or 0),
        "verified_today": int(row.verified_today or 0),
    }


def _verification_base_query(db: Session):
    return db.query(Place).join(City, City.id == Place.city_id)


def _distance_filtered_queue(query, *, lat: float, lng: float, radius_meters: float, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    rows = query.options(joinedload(Place.city)).all()
    items = [_place_queue_payload(place, lat=lat, lng=lng) for place in rows]
    items = [item for item in items if item["distance_meters"] is not None and item["distance_meters"] <= radius_meters]
    items.sort(key=lambda item: (
        0 if item["verification_status"] == "needs_recheck" else 1,
        item["existence_confidence_score"],
        item["distance_meters"] if item["distance_meters"] is not None else 10**12,
        item["place_id"],
    ))
    total = len(items)
    return items[offset : offset + limit], total


def _place_queue_payload(place: Place, *, lat: float | None, lng: float | None) -> dict[str, Any]:
    city = place.city
    distance = _distance_meters(place.lat, place.lng, lat, lng) if lat is not None and lng is not None else None
    return {
        "place_id": place.id,
        "title": place.title,
        "slug": place.slug,
        "city_slug": city.slug if city else None,
        "category": place.category,
        "address": place.address,
        "lat": place.lat,
        "lng": place.lng,
        "distance_meters": distance,
        "existence_confidence_score": place.existence_confidence_score or 0,
        "existence_confidence_level": place.existence_confidence_level or "unknown",
        "verification_status": place.verification_status or "unverified",
        "verification_source": place.verification_source,
        "verification_method": place.verification_method,
        "verified_at": place.verified_at,
        "verified_by": place.verified_by,
        "needs_recheck_at": place.needs_recheck_at,
        "verification_comment": place.verification_comment,
    }


def _enqueue_if_stale(db: Session, state: tuple[int, int], place: Place) -> tuple[int, int]:
    enqueued, existing = state
    if not is_needs_verification(place):
        return state
    if _has_pending_task(db, place.id):
        return enqueued, existing + 1
    db.add(PlaceVerificationTask(place_id=place.id, reason="stale_data", priority=_priority(place)))
    return enqueued + 1, existing


def _has_pending_task(db: Session, place_id: int) -> bool:
    return (
        db.query(PlaceVerificationTask)
        .filter(PlaceVerificationTask.place_id == place_id, PlaceVerificationTask.status == "pending")
        .first()
        is not None
    )


def _priority(place: Place) -> int:
    category = str(getattr(place, "category", "") or "")
    return 10 if category in {"restaurant", "cafe", "coffee", "bar", "food"} else 5


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    value = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)), 2)