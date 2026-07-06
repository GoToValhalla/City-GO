"""
Фильтры списка Place: публичная видимость, город (id/slug), destination membership, категория, тег.
"""

from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from services.city_destination_compatibility import get_destination_by_slug, resolve_destination_to_city_id
from services.destination_places_query import apply_destination_membership_filter, should_use_membership_catalog
from services.place_public_visibility import apply_public_place_visibility

PUBLISHED_CITY_STATUS = "published"


def apply_place_filters(
    db: Session,
    query: Query,
    city_id: int | None = None,
    city_slug: str | None = None,
    destination_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
) -> Query | None:
    if destination_slug is not None:
        return _apply_destination_filter(db, query, destination_slug, category_id, tag_id)

    query = query.join(City, Place.city_id == City.id).filter(
        City.is_active.is_(True),
        City.launch_status == PUBLISHED_CITY_STATUS,
    )
    query = apply_public_place_visibility(query)

    if city_id is not None:
        query = query.filter(Place.city_id == city_id)

    if city_slug is not None:
        city = db.query(City).filter(
            City.slug == city_slug,
            City.is_active.is_(True),
            City.launch_status == PUBLISHED_CITY_STATUS,
        ).first()
        if city is None:
            return None
        query = query.filter(Place.city_id == city.id)

    if category_id is not None:
        query = query.filter(Place.category_id == category_id)

    if tag_id is not None:
        from models.place_tag import PlaceTag

        query = query.join(PlaceTag, Place.id == PlaceTag.place_id).filter(PlaceTag.tag_id == tag_id)

    return query


def _apply_destination_filter(
    db: Session,
    query: Query,
    destination_slug: str,
    category_id: int | None,
    tag_id: int | None,
) -> Query | None:
    dest = get_destination_by_slug(db, destination_slug)
    if dest is None or not dest.is_active:
        return None
    if should_use_membership_catalog():
        query = apply_destination_membership_filter(db, query, dest.id)
    else:
        legacy_city_id = resolve_destination_to_city_id(db, dest)
        if legacy_city_id is None:
            return None
        query = query.join(City, Place.city_id == City.id).filter(
            City.is_active.is_(True),
            City.launch_status == PUBLISHED_CITY_STATUS,
            Place.city_id == legacy_city_id,
        )
        query = apply_public_place_visibility(query)
    if category_id is not None:
        query = query.filter(Place.category_id == category_id)
    if tag_id is not None:
        from models.place_tag import PlaceTag

        query = query.join(PlaceTag, Place.id == PlaceTag.place_id).filter(PlaceTag.tag_id == tag_id)
    return query
