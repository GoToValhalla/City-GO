"""Сборка PlaceRead с публичными изображениями и рейтингами."""

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceRead
from schemas.public_place import PublicPlaceRead
from services.place_data_sanitizer import public_place_payload
from services.place_public_image_service import PublicPlaceImage, resolve_public_place_images, resolve_public_place_images_bulk


def build_place_read(db: Session, place: Place) -> PlaceRead:
    payload = PlaceRead.model_validate(place).model_dump()
    public_images = resolve_public_place_images(db, place)
    _apply_public_images(payload, public_images)
    return PlaceRead(**payload)


def build_place_reads(db: Session, places: list[Place]) -> list[PlaceRead]:
    if not places:
        return []
    if isinstance(places[0], dict):
        return [PlaceRead(**place) for place in places]

    public_by_id = resolve_public_place_images_bulk(db, places)
    result: list[PlaceRead] = []
    for place in places:
        payload = PlaceRead.model_validate(place).model_dump()
        _apply_public_images(payload, public_by_id.get(place.id, []))
        result.append(PlaceRead(**payload))
    return result


def build_public_place_read(db: Session, place: Place) -> PublicPlaceRead:
    images = [image.image_url for image in resolve_public_place_images(db, place) if image.image_url]
    return PublicPlaceRead(**public_place_payload(place, images))


def build_public_place_reads(db: Session, places: list[Place]) -> list[PublicPlaceRead]:
    public_by_id = resolve_public_place_images_bulk(db, places) if places else {}
    return [
        PublicPlaceRead(**public_place_payload(place, [image.image_url for image in public_by_id.get(place.id, []) if image.image_url]))
        for place in places
    ]


def _apply_public_images(payload: dict[str, object], public_images: list[PublicPlaceImage]) -> None:
    urls = [image.image_url for image in public_images if image.image_url]
    payload["image_urls"] = urls or None
    payload["photo_urls"] = urls or None
    if not public_images:
        payload["image_url"] = None
        payload["image_id"] = None
        payload["image_source_type"] = None
        payload["image_attribution"] = None
        payload["image_license"] = None
        payload["image_confidence"] = None
        payload["image_status"] = None
        payload["image_reviewed_at"] = None
        return

    public_image = public_images[0]
    payload["image_url"] = public_image.image_url
    payload["image_id"] = public_image.image_id
    payload["image_source_type"] = public_image.image_source_type
    payload["image_attribution"] = public_image.image_attribution
    payload["image_license"] = public_image.image_license
    payload["image_confidence"] = public_image.image_confidence
    payload["image_status"] = public_image.image_status
    payload["image_reviewed_at"] = public_image.image_reviewed_at
