"""Список мест для Eligibility Dashboard."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.place_quality_score import compute_place_quality_score, quality_bucket
from services.place_quality_signals import has_high_quality_route_core, is_placeholder_title
from services.route_eligibility import evaluate_place_route_eligibility
from services.route_eligibility_dashboard.reasons import dashboard_reasons, primary_reason


QUALITY_BUCKETS = frozenset({"high", "medium", "low"})
READINESS_FILTERS = frozenset({
    "route_ready",
    "catalog_ready",
    "needs_fix",
    "high_quality",
    "low_quality",
    "placeholder",
})


def list_eligibility_places(
    db: Session,
    *,
    city_slug: str | None = None,
    category: str | None = None,
    eligible: bool | None = None,
    no_photo: bool | None = None,
    no_address: bool | None = None,
    no_description: bool | None = None,
    unpublished: bool | None = None,
    inactive: bool | None = None,
    issue: str | None = None,
    readiness: str | None = None,
    quality: str | None = None,
    min_quality_score: int | None = None,
    placeholder_name: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, object]], int]:
    city = _resolve_city(db, city_slug)
    query = db.query(Place)
    if city is not None:
        query = query.filter(Place.city_id == city.id)
    query = _apply_filters(
        query, category=category, no_photo=no_photo, no_address=no_address,
        no_description=no_description, unpublished=unpublished, inactive=inactive,
    )
    rows = query.order_by(Place.id.desc()).all()
    items = [_row(place, city) for place in rows]
    items = _apply_computed_filters(
        items,
        eligible=eligible,
        issue=issue,
        readiness=readiness,
        quality=quality,
        min_quality_score=min_quality_score,
        placeholder_name=placeholder_name,
    )
    total = len(items)
    return items[offset : offset + min(limit, 200)], total


def _row(place: Place, city: City | None) -> dict[str, object]:
    result = evaluate_place_route_eligibility(place, city=city)
    score = compute_place_quality_score(place)
    bucket = quality_bucket(score)
    reasons = dashboard_reasons(place, city=city)
    placeholder = is_placeholder_title(getattr(place, "title", None))
    high_quality_route_candidate = has_high_quality_route_core(place, computed_score=score)
    return {
        "place_id": place.id,
        "title": place.title,
        "slug": place.slug,
        "category": place.category,
        "eligible": result.eligible,
        "quality_score": score,
        "quality_bucket": bucket,
        "reasons": reasons,
        "primary_reason": primary_reason(reasons),
        "city_slug": city.slug if city else None,
        "placeholder_name": placeholder,
        "high_quality_route_candidate": high_quality_route_candidate,
    }


def _resolve_city(db: Session, city_slug: str | None) -> City | None:
    if not city_slug:
        return None
    return db.query(City).filter(City.slug == city_slug).first()


def _apply_filters(
    query: Query,
    *,
    category: str | None,
    no_photo: bool | None,
    no_address: bool | None,
    no_description: bool | None,
    unpublished: bool | None,
    inactive: bool | None,
) -> Query:
    if category:
        query = query.filter(Place.category == category)
    if no_photo:
        query = query.filter(Place.image_url.is_(None))
    if no_address:
        query = query.filter(or_(Place.address.is_(None), Place.address == ""))
    if no_description:
        query = query.filter(or_(Place.short_description.is_(None), Place.short_description == ""))
    if unpublished:
        query = query.filter(Place.is_published.is_(False))
    if inactive:
        query = query.filter(or_(Place.is_active.is_(False), Place.status != "active"))
    return query


def _apply_computed_filters(
    items: list[dict[str, object]],
    *,
    eligible: bool | None,
    issue: str | None,
    readiness: str | None,
    quality: str | None,
    min_quality_score: int | None,
    placeholder_name: bool | None,
) -> list[dict[str, object]]:
    result = items
    if eligible is not None:
        result = [row for row in result if row["eligible"] is eligible]
    if issue:
        result = [row for row in result if issue in row["reasons"] or row["primary_reason"] == issue]
    if quality in QUALITY_BUCKETS:
        result = [row for row in result if row["quality_bucket"] == quality]
    if min_quality_score is not None:
        result = [row for row in result if int(row["quality_score"] or 0) >= min_quality_score]
    if placeholder_name is not None:
        result = [row for row in result if bool(row.get("placeholder_name")) is placeholder_name]
    if readiness in READINESS_FILTERS:
        result = _apply_readiness_filter(result, readiness)
    return result


def _apply_readiness_filter(items: list[dict[str, object]], readiness: str) -> list[dict[str, object]]:
    if readiness == "route_ready":
        return [row for row in items if bool(row["eligible"])]
    if readiness == "catalog_ready":
        return [
            row for row in items
            if row["primary_reason"] not in {"placeholder_title", "no_coordinates", "unpublished_place", "hidden_place"}
        ]
    if readiness == "needs_fix":
        return [row for row in items if not bool(row["eligible"])]
    if readiness == "high_quality":
        return [row for row in items if bool(row.get("high_quality_route_candidate")) and not bool(row.get("placeholder_name"))]
    if readiness == "low_quality":
        return [row for row in items if row["quality_bucket"] == "low" or "low_quality" in row["reasons"]]
    if readiness == "placeholder":
        return [row for row in items if bool(row.get("placeholder_name")) or "placeholder_title" in row["reasons"]]
    return items