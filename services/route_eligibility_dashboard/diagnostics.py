"""City-level route readiness diagnostics for admin UI."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES

BLOCKER_CODES = (
    "no_photo",
    "no_address",
    "hidden_category",
    "draft_or_unpublished",
    "inactive",
    "low_quality",
    "missing_coordinates",
)


def build_route_readiness_diagnostics(db: Session, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
    rows = [_place_row(place, _blockers(place)) for place in places]
    counts = Counter(reason for row in rows for reason in row["blockers"])
    blocked = [row for row in rows if row["blockers"]]
    near_ready = sorted(
        [row for row in blocked if 1 <= len(row["blockers"]) <= 2],
        key=lambda row: (len(row["blockers"]), -int(row["quality_score"]), int(row["place_id"])),
    )
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "places_total": len(places),
        "eligible_places": sum(1 for row in rows if not row["blockers"]),
        "published_places": _published_count(db, city.id),
        "blockers_count_by_reason": {code: int(counts.get(code, 0)) for code in BLOCKER_CODES},
        "near_ready_places": near_ready[:20],
        "sample_blocked_places": blocked[:20],
    }


def _blockers(place: Place) -> list[str]:
    checks = (
        ("no_photo", not bool(place.image_url)),
        ("no_address", not bool((place.address or "").strip())),
        ("hidden_category", _hidden_category(place.category)),
        ("draft_or_unpublished", not _published(place)),
        ("inactive", not _active(place)),
        ("low_quality", int(place.quality_score or 0) < 50),
        ("missing_coordinates", place.lat is None or place.lng is None),
    )
    return [code for code, failed in checks if failed]


def _place_row(place: Place, blockers: list[str]) -> dict[str, object]:
    return {
        "place_id": place.id,
        "title": place.title,
        "slug": place.slug,
        "category": place.category,
        "blockers": blockers,
        "quality_score": int(place.quality_score or 0),
    }


def _hidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in ROUTE_FORBIDDEN_CATEGORIES)


def _published(place: Place) -> bool:
    return bool(place.is_published and place.is_visible_in_catalog and place.publication_status == "published")


def _active(place: Place) -> bool:
    return bool(place.is_active and place.status == "active")


def _published_count(db: Session, city_id: int) -> int:
    return db.query(Place).filter(
        Place.city_id == city_id,
        Place.is_published.is_(True),
        Place.is_visible_in_catalog.is_(True),
        Place.publication_status == "published",
    ).count()
