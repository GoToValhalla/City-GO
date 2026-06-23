import pytest

from services.place_photo_candidate_service import add_photo_candidate, set_primary_photo_candidate


def test_generic_source_photo_cannot_be_exact_primary_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-generic-photo")
    place = place_factory(city_id=city.id, slug="generic-photo", title="Generic Photo", category="park")
    candidate = add_photo_candidate(db_session, place_id=place.id, image_url="https://example.test/generic.jpg",
                                    source_type="unsplash", match_type="exact", confidence=0.95)
    db_session.commit()

    assert candidate.is_primary_candidate is False
    with pytest.raises(ValueError):
        set_primary_photo_candidate(db_session, candidate.id, actor="qa")
