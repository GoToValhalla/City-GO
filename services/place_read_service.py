"""Сборка PlaceRead с публичным изображением и рейтингами."""

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceRead
from services.place_public_image_service import resolve_public_place_image, resolve_public_place_images_bulk


def build_place_read(db: Session, place: Place) -> PlaceRead:
    payload = PlaceRead.model_validate(place).model_dump()
    public_image = resolve_public_place_image(db, place)
    _apply_public_image(payload, public_image)
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
        _apply_public_image(payload, public_by_id.get(place.id))
        result.append(PlaceRead(**payload))
    return result


def _apply_public_image(payload: dict[str, object], public_image) -> None:
    if public_image is None:
        payload["image_url"] = None
        payload["image_id"] = None
        payload["image_source_type"] = None
        payload["image_attribution"] = None
        payload["image_license"] = None
        payload["image_confidence"] = None
        payload["image_status"] = None
        payload["image_reviewed_at"] = None
        return

    payload["image_url"] = public_image.image_url
    payload["image_id"] = public_image.image_id
    payload["image_source_type"] = public_image.image_source_type
    payload["image_attribution"] = public_image.image_attribution
    payload["image_license"] = public_image.image_license
    payload["image_confidence"] = public_image.image_confidence
    payload["image_status"] = public_image.image_status
    payload["image_reviewed_at"] = public_image.image_reviewed_at
