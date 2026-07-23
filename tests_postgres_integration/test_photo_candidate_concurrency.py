"""Photo candidate moderation under real concurrent PostgreSQL sessions --
SQLite's single-connection rollback-per-test fixture cannot model two
genuinely concurrent admin actions racing on the same row lock."""

from __future__ import annotations

import threading

from db.session import SessionLocal
from models.place_image import PlaceImage
from models.place_photo_candidate import PlacePhotoCandidate
from services.place_photo_candidate_service import (
    PhotoCandidateAlreadyDecidedError,
    add_photo_candidate,
    approve_photo_candidate,
    reject_photo_candidate,
)

from conftest import make_published_place


def test_concurrent_approve_and_reject_leave_exactly_one_winner_new(pg_session, pg_city, pg_category) -> None:
    """Two admins racing to approve vs reject the same candidate: the
    row-level FOR UPDATE lock must serialize them so exactly one decision
    wins and the loser observes a truthful PhotoCandidateAlreadyDecidedError
    -- never both succeeding, and never a partially-applied mixed state."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    candidate = add_photo_candidate(
        pg_session, place_id=place.id, image_url="https://example.com/race.jpg",
        source_type="source-a", match_type="direct", confidence=0.9,
    )
    pg_session.commit()
    candidate_id = candidate.id

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def approve() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            approve_photo_candidate(session, candidate_id, actor="admin-approve")
            session.commit()
            with lock:
                outcomes.append("approve_ok")
        except PhotoCandidateAlreadyDecidedError:
            session.rollback()
            with lock:
                outcomes.append("approve_conflict")
        finally:
            session.close()

    def reject() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            reject_photo_candidate(session, candidate_id, actor="admin-reject")
            session.commit()
            with lock:
                outcomes.append("reject_ok")
        except PhotoCandidateAlreadyDecidedError:
            session.rollback()
            with lock:
                outcomes.append("reject_conflict")
        finally:
            session.close()

    threads = [threading.Thread(target=approve), threading.Thread(target=reject)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    successes = [outcome for outcome in outcomes if outcome.endswith("_ok")]
    conflicts = [outcome for outcome in outcomes if outcome.endswith("_conflict")]
    assert len(successes) == 1
    assert len(conflicts) == 1

    reloaded = pg_session.query(PlacePhotoCandidate).filter_by(id=candidate_id).populate_existing().one()
    assert reloaded.status in {"approved", "rejected"}
    if successes[0] == "approve_ok":
        assert reloaded.status == "approved"
        assert reloaded.reviewed_by == "admin-approve"
    else:
        assert reloaded.status == "rejected"
        assert reloaded.reviewed_by == "admin-reject"

    # pg_city's own teardown does not know about PlacePhotoCandidate/PlaceImage
    # (this test file's own concern) -- clean them up here so the shared
    # fixture's Place delete does not hit an FK violation from these rows.
    pg_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).delete()
    pg_session.commit()


def test_concurrent_set_primary_leaves_exactly_one_primary_image_new(pg_session, pg_city, pg_category) -> None:
    """Two admins racing to set two different candidates as primary for
    the same place: the row lock on each candidate plus clear_primary_flags
    must leave exactly one PlaceImage.is_primary=True and place.image_url
    pointing at that same winning candidate -- never two primaries, never
    a place.image_url that disagrees with which PlaceImage is primary."""
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    first = add_photo_candidate(
        pg_session, place_id=place.id, image_url="https://example.com/first.jpg",
        source_type="source-a", match_type="direct", confidence=0.9,
    )
    second = add_photo_candidate(
        pg_session, place_id=place.id, image_url="https://example.com/second.jpg",
        source_type="source-a", match_type="direct", confidence=0.9,
    )
    pg_session.commit()
    place_id, first_id, second_id = place.id, first.id, second.id

    barrier = threading.Barrier(2)

    def set_primary(candidate_id: int) -> None:
        session = SessionLocal()
        try:
            from services.place_photo_candidate_service import set_primary_photo_candidate

            barrier.wait(timeout=5)
            set_primary_photo_candidate(session, candidate_id, actor="admin-primary")
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=set_primary, args=(first_id,)), threading.Thread(target=set_primary, args=(second_id,))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    primary_images = pg_session.query(PlaceImage).filter_by(place_id=place_id, is_primary=True).populate_existing().all()
    assert len(primary_images) == 1
    pg_session.refresh(place)
    assert place.image_url == primary_images[0].image_url

    # See cleanup note in the test above -- pg_city's teardown does not
    # know about these child rows.
    pg_session.query(PlaceImage).filter_by(place_id=place_id).delete()
    pg_session.query(PlacePhotoCandidate).filter_by(place_id=place_id).delete()
    pg_session.commit()
