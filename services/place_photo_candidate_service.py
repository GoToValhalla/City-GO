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

CANDIDATE_STATUS = "candidate"
APPROVED_STATUS = "approved"
REJECTED_STATUS = "rejected"
# The only status a candidate may be moderated from -- a candidate already
# approved or rejected has already been decided, and approval-after-rejection
# / rejection-after-approval must be reported as a truthful conflict, never
# silently re-applied.
_MODERATABLE_FROM_STATUS = CANDIDATE_STATUS


class PhotoCandidateAlreadyDecidedError(ValueError):
    """Raised when approve/reject/set-primary targets a candidate that has
    already been moderated (status is not "candidate")."""

    def __init__(self, candidate_id: int, current_status: str):
        self.candidate_id = candidate_id
        self.current_status = current_status
        super().__init__(f"Photo candidate #{candidate_id} is already {current_status}, not candidate")


def _locked_candidate(db: Session, candidate_id: int) -> PlacePhotoCandidate | None:
    return (
        db.query(PlacePhotoCandidate)
        .filter(PlacePhotoCandidate.id == candidate_id)
        .populate_existing()
        .with_for_update()
        .first()
    )


def add_photo_candidate(
    db: Session,
    *,
    place_id: int,
    image_url: str,
    source_type: str,
    match_type: str,
    confidence: float,
) -> PlacePhotoCandidate:
    item = _pending_photo_candidate(db, place_id=place_id, image_url=image_url)
    item = item or db.query(PlacePhotoCandidate).filter_by(place_id=place_id, image_url=image_url).first()
    item = item or PlacePhotoCandidate(place_id=place_id, image_url=image_url)
    item.source_type = source_type
    item.match_type = match_type
    item.confidence = min(max(confidence, 0.0), 1.0)
    item.status = item.status or "candidate"
    item.is_primary_candidate = not _is_generic(item) and item.confidence >= 0.75
    db.add(item)
    return item


def approve_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    """Approve a photo candidate that is still in "candidate" status.

    Locks the row (SELECT ... FOR UPDATE + populate_existing) so a
    concurrent reject/approve/set-primary on the same candidate cannot
    race past this check. A candidate already "approved" or "rejected"
    raises PhotoCandidateAlreadyDecidedError instead of silently
    re-applying the decision -- approval-after-rejection is a truthful
    conflict, not a no-op success."""
    candidate = _locked_candidate(db, candidate_id)
    if candidate is None:
        return None
    if candidate.status != _MODERATABLE_FROM_STATUS:
        raise PhotoCandidateAlreadyDecidedError(candidate_id, candidate.status)
    candidate.status = APPROVED_STATUS
    candidate.reviewed_by = actor
    candidate.reviewed_at = datetime.utcnow()
    db.add(candidate)
    return candidate


def reject_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    """Reject a photo candidate that is still in "candidate" status.

    Same locking and status-guard discipline as approve_photo_candidate:
    rejection-after-approval raises PhotoCandidateAlreadyDecidedError
    rather than silently overwriting an already-approved decision."""
    candidate = _locked_candidate(db, candidate_id)
    if candidate is None:
        return None
    if candidate.status != _MODERATABLE_FROM_STATUS:
        raise PhotoCandidateAlreadyDecidedError(candidate_id, candidate.status)
    candidate.status = REJECTED_STATUS
    candidate.is_primary_candidate = False
    candidate.reviewed_by = actor
    candidate.reviewed_at = datetime.utcnow()
    db.add(candidate)
    return candidate


def set_primary_photo_candidate(db: Session, candidate_id: int, *, actor: str) -> PlacePhotoCandidate | None:
    """Approve a candidate and make it the place's primary photo, all in
    one locked, atomic operation: candidate.status, the PlaceImage primary
    flags (clear_primary_flags + this image's own is_primary), and
    place.image_url are set together -- no other request can observe a
    state where only some of these have been updated. A candidate already
    approved/rejected by a concurrent request raises
    PhotoCandidateAlreadyDecidedError rather than silently re-promoting a
    rejected image or clobbering another admin's concurrent decision.

    Locking order matters here: candidate rows for the SAME place are
    independent rows, so locking only the candidate does not serialize two
    concurrent set-primary calls for two DIFFERENT candidates of the same
    place -- each could lock its own candidate, then race unlocked on
    clear_primary_flags/PlaceImage, leaving two images marked primary. The
    place row itself is the true shared resource and must be locked FIRST,
    before either the candidate check or any PlaceImage mutation, so the
    second concurrent caller blocks until the first's full transaction
    (place.image_url + PlaceImage flags + candidate status) has committed."""
    place_id = db.query(PlacePhotoCandidate.place_id).filter(PlacePhotoCandidate.id == candidate_id).scalar()
    if place_id is None:
        return None
    place = db.query(Place).filter(Place.id == place_id).with_for_update().first()
    candidate = _locked_candidate(db, candidate_id)
    if candidate is None:
        return None
    if candidate.status != _MODERATABLE_FROM_STATUS:
        raise PhotoCandidateAlreadyDecidedError(candidate_id, candidate.status)
    if _is_generic(candidate):
        raise ValueError("Generic/category fallback photo cannot be primary")
    clear_primary_flags(db, candidate.place_id)
    image = _place_image(db, candidate)
    image.status = PLACE_IMAGE_STATUS_APPROVED
    image.is_primary = True
    if place is not None:
        place.image_url = candidate.image_url
    candidate.status = APPROVED_STATUS
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


def _pending_photo_candidate(db: Session, *, place_id: int, image_url: str) -> PlacePhotoCandidate | None:
    for pending in db.new:
        if isinstance(pending, PlacePhotoCandidate) and pending.place_id == place_id and pending.image_url == image_url:
            return pending
    return None


def _is_generic(candidate: PlacePhotoCandidate) -> bool:
    return candidate.match_type in GENERIC_MATCH_TYPES or candidate.source_type in GENERIC_SOURCE_TYPES
