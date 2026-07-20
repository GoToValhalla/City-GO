"""
Карточка публично видимого места по slug с подгрузкой тегов через join place_tags ↔ tags.
"""

from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from models.tag import Tag
from services.place_public_image_service import resolve_public_place_image
from services.place_public_visibility import apply_public_place_visibility


# Возвращает детальную информацию о публично видимом месте по slug.
# Дополнительно подтягивает связанные теги.
def get_place_detail_by_slug(db: Session, slug: str) -> dict | None:
    query = db.query(Place).filter(Place.slug == slug)
    place = apply_public_place_visibility(query).first()

    if place is None:
        return None

    tags = (
        db.query(Tag)
        .join(PlaceTag, Tag.id == PlaceTag.tag_id)
        .filter(PlaceTag.place_id == place.id)
        .all()
    )

    public_image = resolve_public_place_image(db, place)

    return {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "city_id": place.city_id,
        "category_id": place.category_id,
        "category": place.category,
        "short_description": place.short_description,
        "image_url": public_image.image_url if public_image else None,
        "image_source_type": public_image.image_source_type if public_image else None,
        "image_attribution": public_image.image_attribution if public_image else None,
        "image_license": public_image.image_license if public_image else None,
        "address": place.address,
        "lat": place.lat,
        "lng": place.lng,
        "price_level": place.price_level,
        "dog_friendly": place.dog_friendly,
        "family_friendly": place.family_friendly,
        "indoor": place.indoor,
        "outdoor": place.outdoor,
        "tags": [
            {
                "id": tag.id,
                "code": tag.code,
                "name": tag.name,
            }
            for tag in tags
        ],
    }
