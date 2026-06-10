from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.place_public_image_service import PublicPlaceImage, resolve_public_place_images_bulk


def attach_public_images(db: Session, places: list[Place]) -> list[Place]:
    public_by_id = resolve_public_place_images_bulk(db, places)
    return [_attach(place, public_by_id.get(place.id)) for place in places]


def _attach(place: Place, public_image: PublicPlaceImage | None) -> Place:
    image = _public_image_attrs(public_image)
    for key, value in image.items():
        setattr(place, key, value)
    return place


def _public_image_attrs(public_image: PublicPlaceImage | None) -> dict[str, object]:
    if public_image is None:
        return {
            "public_image_url": None,
            "public_image_id": None,
            "public_image_source_type": None,
            "public_image_attribution": None,
            "public_image_license": None,
            "public_image_confidence": None,
            "public_image_status": None,
        }
    return {
        "public_image_url": public_image.image_url,
        "public_image_id": public_image.image_id,
        "public_image_source_type": public_image.image_source_type,
        "public_image_attribution": public_image.image_attribution,
        "public_image_license": public_image.image_license,
        "public_image_confidence": public_image.image_confidence,
        "public_image_status": public_image.image_status,
    }
