from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.place_image import PlaceImage
from services.place_image_review_service import approve_place_image, reject_place_image


@dataclass(frozen=True)
class MediaModerationResult:
    image_id: int
    place_id: int
    status: str


def approve_media(db: Session, image_id: int, *, actor: str, comment: str | None = None) -> MediaModerationResult:
    return _result(approve_place_image(db, image_id, actor=actor, comment=comment, commit=False))


def reject_media(db: Session, image_id: int, *, actor: str, comment: str | None = None) -> MediaModerationResult:
    return _result(reject_place_image(db, image_id, actor=actor, comment=comment, commit=False))


def _result(image: PlaceImage) -> MediaModerationResult:
    return MediaModerationResult(image_id=image.id, place_id=image.place_id, status=image.status)
