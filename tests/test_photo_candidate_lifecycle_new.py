"""Photo candidate moderation must lock the row, enforce legal status
transitions, and keep candidate status / PlaceImage primary flags /
place.image_url atomic -- approval-after-rejection and rejection-after-
approval must be reported as a truthful conflict, never silently
re-applied."""

from __future__ import annotations

from models.place_image import PlaceImage
from models.place_photo_candidate import PlacePhotoCandidate
from services.place_photo_candidate_service import (
    PhotoCandidateAlreadyDecidedError,
    add_photo_candidate,
    approve_photo_candidate,
    reject_photo_candidate,
    set_primary_photo_candidate,
)

import pytest


def _candidate(db_session, place, *, image_url: str = "https://example.com/a.jpg", confidence: float = 0.9) -> PlacePhotoCandidate:
    item = add_photo_candidate(
        db_session, place_id=place.id, image_url=image_url,
        source_type="source-a", match_type="direct", confidence=confidence,
    )
    db_session.commit()
    return item


def test_approve_after_reject_is_a_truthful_conflict_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    candidate = _candidate(db_session, place)

    reject_photo_candidate(db_session, candidate.id, actor="admin-1")
    db_session.commit()
    candidate_id = candidate.id

    with pytest.raises(PhotoCandidateAlreadyDecidedError):
        approve_photo_candidate(db_session, candidate_id, actor="admin-2")

    reloaded = db_session.query(PlacePhotoCandidate).filter_by(id=candidate_id).one()
    assert reloaded.status == "rejected"
    assert reloaded.reviewed_by == "admin-1"


def test_reject_after_approve_is_a_truthful_conflict_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    candidate = _candidate(db_session, place)

    approve_photo_candidate(db_session, candidate.id, actor="admin-1")
    db_session.commit()
    candidate_id = candidate.id

    with pytest.raises(PhotoCandidateAlreadyDecidedError):
        reject_photo_candidate(db_session, candidate_id, actor="admin-2")

    reloaded = db_session.query(PlacePhotoCandidate).filter_by(id=candidate_id).one()
    assert reloaded.status == "approved"
    assert reloaded.reviewed_by == "admin-1"


def test_set_primary_after_reject_is_a_truthful_conflict_new(db_session, place_factory) -> None:
    place = place_factory(title="Место")
    candidate = _candidate(db_session, place)

    reject_photo_candidate(db_session, candidate.id, actor="admin-1")
    db_session.commit()
    candidate_id = candidate.id

    with pytest.raises(PhotoCandidateAlreadyDecidedError):
        set_primary_photo_candidate(db_session, candidate_id, actor="admin-2")

    reloaded = db_session.query(PlacePhotoCandidate).filter_by(id=candidate_id).one()
    assert reloaded.status == "rejected"
    assert reloaded.is_primary_candidate is False


def test_set_primary_photo_candidate_is_atomic_new(db_session, place_factory) -> None:
    """candidate.status, the PlaceImage primary flag, and place.image_url
    must all reflect the same decision after set_primary_photo_candidate --
    proving no partial state (e.g. candidate approved but image_url still
    pointing at the old photo) can be observed."""
    place = place_factory(title="Место", image_url=None)
    candidate = _candidate(db_session, place, image_url="https://example.com/primary.jpg")

    result = set_primary_photo_candidate(db_session, candidate.id, actor="admin-1")
    db_session.commit()

    assert result.status == "approved"
    assert result.is_primary_candidate is True
    db_session.refresh(place)
    assert place.image_url == "https://example.com/primary.jpg"
    image = db_session.query(PlaceImage).filter_by(place_id=place.id, image_url="https://example.com/primary.jpg").one()
    assert image.is_primary is True


def test_set_primary_clears_previous_primary_flag_new(db_session, place_factory) -> None:
    place = place_factory(title="Место", image_url=None)
    first = _candidate(db_session, place, image_url="https://example.com/first.jpg")
    second = _candidate(db_session, place, image_url="https://example.com/second.jpg")

    set_primary_photo_candidate(db_session, first.id, actor="admin-1")
    db_session.commit()
    set_primary_photo_candidate(db_session, second.id, actor="admin-1")
    db_session.commit()

    db_session.refresh(place)
    assert place.image_url == "https://example.com/second.jpg"
    first_image = db_session.query(PlaceImage).filter_by(place_id=place.id, image_url="https://example.com/first.jpg").one()
    second_image = db_session.query(PlaceImage).filter_by(place_id=place.id, image_url="https://example.com/second.jpg").one()
    assert first_image.is_primary is False
    assert second_image.is_primary is True


def test_approve_locks_row_for_update_new(db_session, place_factory, monkeypatch) -> None:
    place = place_factory(title="Место")
    candidate = _candidate(db_session, place)

    calls: list[str] = []
    from sqlalchemy.orm import Query

    original = Query.with_for_update

    def spy(self, *args, **kwargs):
        calls.append("with_for_update")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Query, "with_for_update", spy)

    approve_photo_candidate(db_session, candidate.id, actor="admin-1")

    assert "with_for_update" in calls
