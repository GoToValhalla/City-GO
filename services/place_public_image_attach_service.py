from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.place_public_image_service import PublicPlaceImage, resolve_public_place_images_bulk


def attach_public_images(db: Session, places: list[Place]) -> list[Place]:
    public_by_id = resolve_public_place_images_bulk(db, places)
    return [_attach(place, public_by_id.get(place.id, [])) for place in places]


def _attach(place: Place, public_images: list[PublicPlaceImage] | None) -> Place:
    images = public_images or []
    primary = images[0] if images else None
    urls = [image.image_url for image in images if image.image_url]
    attrs = _public_image_attrs(primary)
    place.public_image_url = attrs["public_image_url"]
    place.public_image_id = attrs["public_image_id"]
    place.public_image_source_type = attrs["public_image_source_type"]
    place.public_image_attribution = attrs["public_image_attribution"]
    place.public_image_license = attrs["public_image_license"]
    place.public_image_confidence = attrs["public_image_confidence"]
    place.public_image_status = attrs["public_image_status"]
    place.public_image_urls = urls or None
    place.public_photo_urls = urls or None
    place.image_urls = urls or None
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
