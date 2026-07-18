from __future__ import annotations

from services.admin_service import verify_place


def _create_payload(city_id: int, **overrides):
    payload = {
        "city_id": city_id,
        "slug": "boundary-created-place",
        "title": "Boundary Created Place",
        "lat": 54.9,
        "lng": 20.4,
        "category": "museum",
    }
    payload.update(overrides)
    return payload


def test_admin_create_rejects_explicit_publication_state(client, city_factory) -> None:
    city = city_factory(slug="create-boundary-city")
    response = client.post(
        "/admin/places",
        json=_create_payload(city.id, is_published=True, publication_status="published"),
    )
    assert response.status_code == 422


def test_admin_create_without_publication_fields_creates_canonical_draft(client, city_factory) -> None:
    city = city_factory(slug="create-draft-city")
    response = client.post("/admin/places", json=_create_payload(city.id))
    assert response.status_code == 200
    body = response.json()
    assert body["publication_status"] == "draft"
    assert body["is_published"] is False
    assert body["is_visible_in_catalog"] is False
    assert body["is_route_eligible"] is False
    assert body["is_searchable"] is False


def test_single_verify_is_idempotent(db_session, draft_place_factory) -> None:
    place = draft_place_factory(slug="single-verify-idempotent")
    first = verify_place(db_session, place.id, actor="test-admin")
    second = verify_place(db_session, place.id, actor="test-admin")
    assert first is not None
    assert second is not None
    assert second.verification_status == "verified"
    assert second.existence_confidence_level == "high"
    assert second.verified_at is not None


def test_bulk_verify_rejects_verified_noop(db_session, draft_place_factory) -> None:
    from services.admin_place_bulk_service import apply_bulk

    place = draft_place_factory(slug="bulk-verify-noop")
    verify_place(db_session, place.id, actor="test-admin")
    result = apply_bulk(db_session, [place.id], "verify", {}, actor="test-admin")
    assert result["applied"] == 0
    assert result["failed"] == 1
    assert "уже подтверждено" in result["errors"][0]["error"]
