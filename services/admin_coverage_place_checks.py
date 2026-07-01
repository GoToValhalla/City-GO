"""Проверки качества мест для admin Data Coverage (published scope)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.place_address_policy import is_generic_address, is_real_address
from services.place_public_image_service import resolve_public_place_images_bulk


def place_has_coverage_address(place: Place) -> bool:
    if not is_real_address(place.address):
        return False
    return not is_generic_address(place.address, place.category)


def place_has_coverage_description(place: Place) -> bool:
    return bool((place.short_description or "").strip())


def published_quality_counts(
    db: Session,
    published_places: list[Place],
) -> tuple[int, int, int, int, int, int]:
    """Возвращает with/without photo, address, description для опубликованных мест."""
    public_by_id = resolve_public_place_images_bulk(db, published_places)
    with_photo = sum(1 for place in published_places if bool(public_by_id.get(place.id)))
    with_addr = sum(1 for place in published_places if place_has_coverage_address(place))
    with_desc = sum(1 for place in published_places if place_has_coverage_description(place))
    published = len(published_places)
    return (
        with_photo,
        published - with_photo,
        with_addr,
        published - with_addr,
        with_desc,
        published - with_desc,
    )
