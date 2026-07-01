from __future__ import annotations

from models.place_image import PLACE_IMAGE_STATUS_ACTIVE, PLACE_IMAGE_STATUS_APPROVED, PLACE_IMAGE_STATUS_REJECTED, PlaceImage
from services.place_read_service import build_place_read


def test_place_read_returns_public_image_gallery_with_primary_first(db_session, city_factory, place_factory):
    city = city_factory(slug="gallery-city", name="Gallery City")
    place = place_factory(city_id=city.id, slug="gallery-place", title="Gallery Place", source="manual", image_url="https://legacy.example.com/photo.jpg")
    secondary = PlaceImage(place_id=place.id, image_url="https://example.com/two.jpg", source_type="manual", status=PLACE_IMAGE_STATUS_ACTIVE, is_primary=False, confidence=0.8)
    primary = PlaceImage(place_id=place.id, image_url="https://example.com/one.jpg", source_type="manual", status=PLACE_IMAGE_STATUS_APPROVED, is_primary=True, confidence=0.9)
    rejected = PlaceImage(place_id=place.id, image_url="https://example.com/rejected.jpg", source_type="manual", status=PLACE_IMAGE_STATUS_REJECTED, is_primary=False, confidence=0.9)
    db_session.add_all([secondary, primary, rejected])
    db_session.commit()
    db_session.refresh(place)

    payload = build_place_read(db_session, place)

    assert payload.image_url == "https://example.com/one.jpg"
    assert payload.image_urls == ["https://example.com/one.jpg", "https://example.com/two.jpg", "https://legacy.example.com/photo.jpg"]
    assert payload.photo_urls == payload.image_urls
    assert "https://example.com/rejected.jpg" not in payload.image_urls
