from datetime import datetime

import pytest

import models.place_image  # noqa: F401 — регистрация таблицы в Base.metadata
from models.place_image import (
    PLACE_IMAGE_STATUS_APPROVED,
    PLACE_IMAGE_STATUS_NEEDS_REVIEW,
    PLACE_IMAGE_STATUS_REJECTED,
    PlaceImage,
)
from services.place_image_review_service import (
    approve_place_image,
    get_pending_place_images,
    reject_place_image,
    set_primary_place_image,
)
from services.place_public_image_service import resolve_public_place_image


@pytest.fixture
def place_image_factory(db_session, place_factory):
    def create_image(
        *,
        place=None,
        image_url: str = "https://example.com/photo.jpg",
        status: str = PLACE_IMAGE_STATUS_NEEDS_REVIEW,
        is_primary: bool = False,
        source_type: str = "osm_image",
    ) -> PlaceImage:
        target_place = place or place_factory()
        image = PlaceImage(
            place_id=target_place.id,
            image_url=image_url,
            source_type=source_type,
            status=status,
            is_primary=is_primary,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(image)
        db_session.commit()
        db_session.refresh(image)
        return image

    return create_image


def test_get_pending_place_images_returns_queue(db_session, place_factory, place_image_factory):
    place = place_factory(slug="cafe-one", title="Cafe One")
    place_image_factory(place=place)

    items, total = get_pending_place_images(db_session, city_slug="zelenogradsk", limit=10, offset=0)

    assert total == 1
    assert items[0]["place_title"] == "Cafe One"
    assert items[0]["status"] == PLACE_IMAGE_STATUS_NEEDS_REVIEW


def test_approve_place_image_sets_review_fields_and_primary(db_session, place_image_factory):
    image = place_image_factory()

    approved = approve_place_image(db_session, image.id, actor="owner", comment="looks correct")

    assert approved.status == PLACE_IMAGE_STATUS_APPROVED
    assert approved.reviewed_by == "owner"
    assert approved.review_comment == "looks correct"
    assert approved.reviewed_at is not None
    assert approved.is_primary is True


def test_reject_place_image_hides_from_public_api(db_session, place_factory, place_image_factory):
    place = place_factory()
    image = place_image_factory(place=place, status=PLACE_IMAGE_STATUS_NEEDS_REVIEW)

    rejected = reject_place_image(db_session, image.id, actor="owner", comment="wrong place")

    assert rejected.status == PLACE_IMAGE_STATUS_REJECTED
    assert rejected.is_primary is False
    assert resolve_public_place_image(db_session, place) is None


def test_set_primary_place_image_requires_approved(db_session, place_image_factory):
    image = place_image_factory(status=PLACE_IMAGE_STATUS_NEEDS_REVIEW)

    with pytest.raises(ValueError):
        set_primary_place_image(db_session, image.id)


def test_public_api_uses_only_approved_image(db_session, place_factory, place_image_factory):
    place = place_factory()
    place.image_url = "https://example.com/rejected.jpg"
    db_session.commit()
    place_image_factory(
        place=place,
        image_url="https://example.com/rejected.jpg",
        status=PLACE_IMAGE_STATUS_REJECTED,
    )
    approved = place_image_factory(
        place=place,
        image_url="https://example.com/approved.jpg",
        status=PLACE_IMAGE_STATUS_APPROVED,
        is_primary=True,
    )

    public_image = resolve_public_place_image(db_session, place)

    assert public_image is not None
    assert public_image.image_url == approved.image_url
