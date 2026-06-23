"""Photo candidate operations with generic/category fallback safety."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.place_photo_candidate import PlacePhotoCandidate
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PlaceImage
from services.place_public_image_service import clear_primary_flags

GENERIC_MATCH_TYPES = {"generic", "category_fallback", "unsplash_category"}
GENERIC_SOURCE_TYPES = {"generic", "category_fallback", "unsplash", "unsplash_category"}


def add_photo_candidate(
    db: Session,
    *,
    place_id: int,
    image_url: str,
    source_type: str,
    match_type: str,
    confidence: float,
) -> PlacePhotoCandidate:
    item = db.query(PlacePhotoCandidate).filter_by(place_id=place_id, image_url=image_url).first()
    item = item or PlacePhotoCandidate(place_id=place_id, image_url=image_url)
    item.source_type = source_type
    item.match_type = match_type
    item.confidence = min(max(confidence, 0.0), 1.0)
    item.status = item.status or "candidate"
    item.is_primary_candidate = not _is_generic(item) and item.confidence >= 0.75
    db.add(item)
    return item


def approve_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    candidate = db.query(PlacePhotoCandidate).filter(PlacePhotoCandidate.id == candidate_id).first()
    if candidate is None:
        return None
    candidate.status = "approved"
    candidate.reviewed_by = actor
    candidate.reviewed_at = datetime.utcnow()
    db.add(candidate)
    return candidate


def reject_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    candidate = db.query(PlacePhotoCandidate).filter(PlacePhotoCandidate.id == candidate_id).first()
    if candidate is None:
        return None
    candidate.status = "rejected"
    candidate.is_primary_candidate = False
    candidate.reviewed_by = actor
    candidate.reviewed_at = datetime.utcnow()
    db.add(candidate)
    return candidate


def set_primary_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    candidate = db.query(PlacePhotoCandidate).filter(PlacePhotoCandidate.id == candidate_id).first()
    if candidate is None:
        return None
    if _is_generic(candidate):
        raise ValueError("Generic/category fallback photo cannot be primary")
    clear_primary_flags(db, candidate.place_id)
    image = _place_image(db, candidate)
    image.status = PLACE_IMAGE_STATUS_APPROVED
    image.is_primary = True
    place = db.query(Place).filter(Place.id == candidate.place_id).first()
    if place is not None:
        place.image_url = candidate.image_url
    candidate.status = "approved"
    candidate.is_primary_candidate = True
    candidate.reviewed_by = actor
    candidate.reviewed_at = datetime.utcnow()
    db.add_all([candidate, image])
    return candidate


def _place_image(db: Session, candidate: PlacePhotoCandidate) -> PlaceImage:
    image = db.query(PlaceImage).filter_by(place_id=candidate.place_id, image_url=candidate.image_url).first()
    if image is not None:
        return image
    return PlaceImage(
        place_id=candidate.place_id,
        image_url=candidate.image_url,
        thumbnail_url=candidate.thumbnail_url,
        source_type=candidate.source_type,
        source_url=candidate.source_url,
        confidence=candidate.confidence,
    )


def _is_generic(candidate: PlacePhotoCandidate) -> bool:
    return candidate.match_type in GENERIC_MATCH_TYPES or candidate.source_type in GENERIC_SOURCE_TYPES
