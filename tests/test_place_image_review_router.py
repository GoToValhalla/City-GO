from datetime import datetime

import models.place_image  # noqa: F401
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage


def test_admin_pending_endpoint_returns_queue(client, db_session, place_factory):
    place = place_factory(slug="review-cafe", title="Review Cafe")
    db_session.add(
        PlaceImage(
            place_id=place.id,
            image_url="https://example.com/pending.jpg",
            source_type="osm_image",
            status=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    response = client.get("/admin/place-images/pending", params={"city_slug": "zelenogradsk"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["place_title"] == "Review Cafe"


def test_admin_approve_and_reject_change_status(client, db_session, place_factory):
    place = place_factory()
    image = PlaceImage(
        place_id=place.id,
        image_url="https://example.com/card.jpg",
        source_type="osm_image",
        status=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(image)
    db_session.commit()

    approve_response = client.post(
        f"/admin/place-images/{image.id}/approve",
        json={"reviewer": "admin", "comment": "ok"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    reject_response = client.post(
        f"/admin/place-images/{image.id}/reject",
        json={"reviewer": "admin", "comment": "no"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"


def test_public_places_do_not_expose_pending_images(client, db_session, place_factory):
    place = place_factory(slug="hidden-photo", title="Hidden Photo")
    place.image_url = "https://example.com/legacy.jpg"
    place.source = "osm"
    db_session.commit()
    db_session.add(
        PlaceImage(
            place_id=place.id,
            image_url="https://example.com/pending-only.jpg",
            source_type="osm_image",
            status=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    response = client.get("/places/", params={"city_slug": "zelenogradsk"})

    assert response.status_code == 200
    item = next(row for row in response.json()["items"] if row["slug"] == "hidden-photo")
    assert item["image_url"] is None
