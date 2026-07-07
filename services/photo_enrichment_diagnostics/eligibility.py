"""DB eligibility counts for photo enrichment diagnostics."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models.place import Place
from models.place_image import PUBLIC_PLACE_IMAGE_STATUSES, PlaceImage
from services.place_public_visibility import is_public_hidden_category

BAD_TITLE_PATTERN = re.compile(r"^(yes|no|unknown|fixme|todo|n/a)$", re.I)


def without_photo_total(db: Session, *, city_id: int) -> int:
    return db.query(Place).filter(Place.city_id == city_id, Place.image_url.is_(None)).count()


def pending_photos_existing(db: Session, *, city_id: int) -> int:
    from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW

    return (
        db.query(PlaceImage)
        .join(Place, Place.id == PlaceImage.place_id)
        .filter(Place.city_id == city_id, PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)
        .count()
    )


def eligible_for_photo_search(db: Session, *, city_id: int) -> int:
    public_image_exists = (
        db.query(PlaceImage.id)
        .filter(PlaceImage.place_id == Place.id, PlaceImage.status.in_(tuple(PUBLIC_PLACE_IMAGE_STATUSES)))
        .exists()
    )
    return (
        db.query(Place)
        .filter(Place.city_id == city_id, Place.status == "active", ~public_image_exists)
        .count()
    )


def filtered_out_by_reason(db: Session, *, city_id: int) -> dict[str, int]:
    # ponytail: select only the scalar columns the loop actually reads, not full ORM
    # rows, since this runs on every admin import job details request for the whole city.
    rows = (
        db.query(
            Place.is_published,
            Place.is_visible_in_catalog,
            Place.category,
            Place.lat,
            Place.lng,
            Place.status,
            Place.is_spam_poi,
            Place.title,
            Place.is_route_eligible,
        )
        .filter(Place.city_id == city_id, Place.image_url.is_(None))
        .all()
    )
    counts = {
        "unpublished_or_hidden": 0,
        "service_category": 0,
        "missing_coordinates": 0,
        "inactive_place": 0,
        "existing_photo": 0,
        "low_quality_title": 0,
        "not_route_eligible": 0,
    }
    for is_published, is_visible_in_catalog, category, lat, lng, status, is_spam_poi, title_raw, is_route_eligible in rows:
        if is_published is not True or is_visible_in_catalog is not True:
            counts["unpublished_or_hidden"] += 1
        if is_public_hidden_category(category):
            counts["service_category"] += 1
        if lat is None or lng is None:
            counts["missing_coordinates"] += 1
        if status != "active":
            counts["inactive_place"] += 1
        if is_spam_poi:
            counts["low_quality_title"] += 1
        title = (title_raw or "").strip()
        if len(title) < 2 or BAD_TITLE_PATTERN.match(title):
            counts["low_quality_title"] += 1
        if is_route_eligible is not True:
            counts["not_route_eligible"] += 1
    return {key: value for key, value in counts.items() if value > 0}
