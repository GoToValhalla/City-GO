from __future__ import annotations

from models.place_photo_candidate import PlacePhotoCandidate
from services.place_photo_candidate_service import add_photo_candidate


def test_add_photo_candidate_deduplicates_pending_candidates_before_commit(db_session, city_factory, place_factory):
    city = city_factory(slug="photo-candidate-dedupe", name="Photo Candidate Dedupe")
    place = place_factory(city_id=city.id, slug="photo-candidate-dedupe-place", title="Photo Candidate Dedupe Place")
    image_url = "https://www.openstreetmap.org/assets/osm_logo_256-test.png"

    first = add_photo_candidate(
        db_session,
        place_id=place.id,
        image_url=image_url,
        source_type="openstreetmap",
        match_type="generic",
        confidence=0.3,
    )
    second = add_photo_candidate(
        db_session,
        place_id=place.id,
        image_url=image_url,
        source_type="openstreetmap",
        match_type="generic",
        confidence=0.4,
    )
    db_session.commit()

    rows = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id, image_url=image_url).all()
    assert first is second
    assert len(rows) == 1
    assert rows[0].confidence == 0.4


def test_add_photo_candidate_reuses_existing_candidate(db_session, city_factory, place_factory):
    city = city_factory(slug="photo-candidate-existing", name="Photo Candidate Existing")
    place = place_factory(city_id=city.id, slug="photo-candidate-existing-place", title="Photo Candidate Existing Place")
    image_url = "https://example.com/photo.jpg"

    add_photo_candidate(
        db_session,
        place_id=place.id,
        image_url=image_url,
        source_type="source-a",
        match_type="direct",
        confidence=0.6,
    )
    db_session.commit()

    reused = add_photo_candidate(
        db_session,
        place_id=place.id,
        image_url=image_url,
        source_type="source-b",
        match_type="direct",
        confidence=0.9,
    )
    db_session.commit()

    rows = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id, image_url=image_url).all()
    assert len(rows) == 1
    assert reused.id == rows[0].id
    assert rows[0].source_type == "source-b"
    assert rows[0].confidence == 0.9
