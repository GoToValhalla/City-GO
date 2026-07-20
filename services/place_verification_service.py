from __future__ import annotations

import math
from datetime import datetime
from functools import reduce
from typing import Any

from sqlalchemy import case, func, text
from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.place import Place
from models.place_verification import PlaceVerification
from models.place_verification_task import PlaceVerificationTask
from schemas.place_verification import PlaceVerificationEnqueueSummary
from services.place_staleness_policy import is_needs_verification
from services.place_verification_mutation import transition_place_verification
from services.publication_state_writer import (
    REASON_DUPLICATE_SUSPECTED,
    REASON_LOW_CONFIDENCE,
    REASON_POLICY_GATE_FAILED,
    transition_place_publication,
)

CONFIDENCE_LEVELS = ((95, "verified"), (80, "high"), (60, "medium"), (30, "low"), (0, "unknown"))


def confidence_level(score: int) -> str:
    for threshold, level in CONFIDENCE_LEVELS:
        if score >= threshold:
            return level
    return "unknown"


def enqueue_stale_places(db: Session, city_slug: str) -> PlaceVerificationEnqueueSummary:
    places = db.query(Place).join(City).filter(City.slug == city_slug).all()
    enqueued, existing = reduce(lambda state, place: _enqueue_if_stale(db, state, place), places, (0, 0))
    db.commit()
    return PlaceVerificationEnqueueSummary(city_slug=city_slug, enqueued=enqueued, already_pending=existing)


def pending_verification_tasks(db: Session, limit: int = 100) -> list[PlaceVerificationTask]:
    return db.query(PlaceVerificationTask).filter(PlaceVerificationTask.status == "pending").order_by(PlaceVerificationTask.priority.desc(), PlaceVerificationTask.created_at.asc()).limit(limit).all()


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
    if city_slug: query = query.filter(City.slug == city_slug)
    if status: query = query.filter(Place.verification_status == status)
    if confidence_level_filter: query = query.filter(Place.existence_confidence_level == confidence_level_filter)
    if max_confidence is not None: query = query.filter(Place.existence_confidence_score <= max_confidence)
    if category: query = query.filter(Place.category == category)
    if radius_meters is not None and lat is not None and lng is not None:
        return _distance_filtered_queue(query, lat=lat, lng=lng, radius_meters=radius_meters, limit=limit, offset=offset)
    total = query.count()
    rows = query.options(joinedload(Place.city)).order_by(
        case((Place.verification_status == "needs_recheck", 0), else_=1),
        func.coalesce(Place.existence_confidence_score, 0).asc(),
        Place.id.asc(),
    ).offset(offset).limit(limit).all()
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
    place = db.query(Place).filter(Place.id == place_id).with_for_update().populate_existing().one_or_none()
    if place is None:
        raise LookupError(f"Place {place_id} not found")
    distance = _distance_meters(place.lat, place.lng, verifier_lat, verifier_lng) if verifier_lat is not None and verifier_lng is not None else None
    score_before = int(place.existence_confidence_score or 0)
    level_before = place.existence_confidence_level or confidence_level(score_before)
    actor = verifier or "local_admin"
    source = "field_visit" if distance is not None else "manual_admin"
    result = _verification_result(
        action,
        score_before=score_before,
        onsite=distance is not None,
        current_status=place.status,
    )
    now = datetime.utcnow()
    try:
        transition_place_verification(
            db, place,
            to_status=result["verification_status"],
            actor=actor,
            reason=comment,
            action=f"place_verification_{action}",
            verification_source=source,
            verification_method=result["method"],
            confidence_score=result["score"],
            confidence_level=confidence_level(result["score"]),
            set_verified_at=action != "needs_recheck",
        )
        if result["place_status"] is not None:
            place.status = result["place_status"]
        _apply_publication_consequence(db, place, action=action, actor=actor, comment=comment)
        db.add(PlaceVerification(
            place_id=place.id,
            status=result["verification_status"],
            confidence_score_before=score_before,
            confidence_score_after=result["score"],
            confidence_level_before=level_before,
            confidence_level_after=confidence_level(result["score"]),
            verification_source=source,
            verification_method=result["method"],
            verifier=actor,
            verifier_lat=verifier_lat,
            verifier_lng=verifier_lng,
            distance_to_place_meters=distance,
            photo_url=photo_url,
            comment=comment,
            created_at=now,
        ))
        db.commit()
        db.refresh(place)
        return place
    except Exception:
        db.rollback()
        raise


def _verification_result(action: str, *, score_before: int, onsite: bool, current_status: str | None) -> dict[str, Any]:
    method = "onsite_confirmed" if onsite else "manual_override"
    active_status = "active" if current_status in {None, "draft", "needs_review"} else current_status
    mapping: dict[str, dict[str, Any]] = {
        "exists": {"verification_status": "verified", "score": 100, "method": method, "place_status": active_status},
        "not_found": {"verification_status": "not_found", "score": 15, "method": method, "place_status": "needs_review"},
        "closed": {"verification_status": "closed", "score": 0, "method": method, "place_status": "closed"},
        "moved": {"verification_status": "moved", "score": 40, "method": method, "place_status": "needs_review"},
        "duplicate": {"verification_status": "duplicate", "score": 0, "method": "manual_override", "place_status": "rejected"},
        "needs_recheck": {"verification_status": "needs_recheck", "score": min(score_before, 50), "method": "manual_override", "place_status": current_status},
    }
    if action not in mapping:
        raise ValueError(f"Unsupported verification action: {action}")
    return mapping[action]


def _apply_publication_consequence(db: Session, place: Place, *, action: str, actor: str, comment: str | None) -> None:
    if action in {"exists", "needs_recheck"}:
        return
    details = {"verification_action": action}
    if action == "duplicate":
        transition_place_publication(db, place, to_status="rejected", reason_code=REASON_DUPLICATE_SUSPECTED, actor=actor, source="place_verification", reason_details=details, human_comment=comment, lock_place=False)
    elif action in {"closed", "not_found"}:
        transition_place_publication(db, place, to_status="hidden", reason_code=REASON_POLICY_GATE_FAILED, actor=actor, source="place_verification", reason_details=details, human_comment=comment, lock_place=False)
    else:
        transition_place_publication(db, place, to_status="needs_review", reason_code=REASON_LOW_CONFIDENCE, actor=actor, source="place_verification", reason_details=details, human_comment=comment, lock_place=False)


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
    return apply_place_verification(db, place_id, action="exists", verifier=verifier or "local_admin", verifier_lat=verifier_lat, verifier_lng=verifier_lng, comment=comment)


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
        if status in {"verified", "trusted"}: verified += 1
        if level == "high": high += 1
        elif level == "medium": medium += 1
        elif level == "low": low += 1
        else: unknown += 1
        if status == "needs_recheck": needs_recheck += 1
        if status == "closed": closed += 1
        if status == "not_found": not_found += 1
        bucket = level if level in {"high", "medium", "low"} else "unknown"
        if status in {"verified", "trusted"}: bucket = "verified"
        inc(category_name, bucket)
    return {
        "city_slug": city_slug, "total_places": total, "verified_count": verified,
        "high_count": high, "medium_count": medium, "low_count": low,
        "unknown_count": unknown, "needs_recheck_count": needs_recheck,
        "closed_count": closed, "not_found_count": not_found,
        "verified_percent": round((verified / total) * 100, 2) if total else 0.0,
        "categories": categories,
    }


def place_verification_summary(db: Session, city_slug: str | None = None) -> dict[str, int]:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    params: dict[str, object] = {"today_start": today_start}
    join_city = ""
    city_filter = ""
    if city_slug:
        join_city = "JOIN cities ON cities.id = places.city_id"
        city_filter = "WHERE cities.slug = :city_slug"
        params["city_slug"] = city_slug
    row = db.execute(text(f"""
        WITH filtered_places AS (
            SELECT places.verification_status, places.existence_confidence_level, places.verified_at
            FROM places {join_city} {city_filter}
        )
        SELECT
            SUM(CASE WHEN verification_status IN ('needs_recheck', 'unverified') OR verification_status IS NULL THEN 1 ELSE 0 END) AS queue_total,
            SUM(CASE WHEN verification_status = 'needs_recheck' THEN 1 ELSE 0 END) AS needs_recheck,
            SUM(CASE WHEN verification_status = 'unverified' OR verification_status IS NULL THEN 1 ELSE 0 END) AS unverified,
            SUM(CASE WHEN existence_confidence_level IN ('low', 'unknown') OR existence_confidence_level IS NULL THEN 1 ELSE 0 END) AS low_confidence,
            SUM(CASE WHEN verification_status IN ('verified', 'trusted') AND verified_at >= :today_start THEN 1 ELSE 0 END) AS verified_today
        FROM filtered_places
    """), params).mappings().one()
    return {key: int(row[key] or 0) for key in ("queue_total", "needs_recheck", "unverified", "low_confidence", "verified_today")}


def _verification_base_query(db: Session):
    return db.query(Place).join(City, City.id == Place.city_id)


def _distance_filtered_queue(query, *, lat: float, lng: float, radius_meters: float, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    rows = query.options(joinedload(Place.city)).all()
    items = [_place_queue_payload(place, lat=lat, lng=lng) for place in rows]
    items = [item for item in items if item["distance_meters"] is not None and item["distance_meters"] <= radius_meters]
    items.sort(key=lambda item: (0 if item["verification_status"] == "needs_recheck" else 1, item["existence_confidence_score"], item["distance_meters"] if item["distance_meters"] is not None else 10**12, item["place_id"]))
    total = len(items)
    return items[offset: offset + limit], total


def _place_queue_payload(place: Place, *, lat: float | None, lng: float | None) -> dict[str, Any]:
    city = place.city
    distance = _distance_meters(place.lat, place.lng, lat, lng) if lat is not None and lng is not None else None
    return {
        "place_id": place.id, "title": place.title, "slug": place.slug,
        "city_slug": city.slug if city else None, "category": place.category,
        "address": place.address, "lat": place.lat, "lng": place.lng,
        "distance_meters": distance,
        "existence_confidence_score": place.existence_confidence_score or 0,
        "existence_confidence_level": place.existence_confidence_level or "unknown",
        "verification_status": place.verification_status or "unverified",
        "verification_source": place.verification_source,
        "verification_method": place.verification_method,
        "verified_at": place.verified_at, "verified_by": place.verified_by,
        "needs_recheck_at": place.needs_recheck_at,
        "verification_comment": place.verification_comment,
    }


def _enqueue_if_stale(db: Session, state: tuple[int, int], place: Place) -> tuple[int, int]:
    enqueued, existing = state
    if not is_needs_verification(place): return state
    if _has_pending_task(db, place.id): return enqueued, existing + 1
    db.add(PlaceVerificationTask(place_id=place.id, reason="stale_data", priority=_priority(place)))
    return enqueued + 1, existing


def _has_pending_task(db: Session, place_id: int) -> bool:
    return db.query(PlaceVerificationTask).filter(PlaceVerificationTask.place_id == place_id, PlaceVerificationTask.status == "pending").first() is not None


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
