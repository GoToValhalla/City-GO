from __future__ import annotations


def _ordinary_put_payload(place, **overrides):
    payload = {
        "city_id": place.city_id,
        "category_id": place.category_id,
        "slug": place.slug,
        "title": place.title,
        "lat": place.lat,
        "lng": place.lng,
        "status": place.status,
    }
    payload.update(overrides)
    return payload


def test_legacy_admin_put_rejects_publication_field(client, db_session, published_place_factory) -> None:
    place = published_place_factory(slug="legacy-put-publication-field")
    response = client.put(
        f"/admin/places/{place.id}",
        json=_ordinary_put_payload(place, publication_status="hidden"),
    )
    assert response.status_code == 422
    db_session.refresh(place)
    assert place.publication_status == "published"
    assert place.is_published is True


def test_legacy_admin_put_rejects_publication_alias(client, db_session, published_place_factory) -> None:
    place = published_place_factory(slug="legacy-put-publication-alias")
    response = client.put(
        f"/admin/places/{place.id}",
        json=_ordinary_put_payload(place, visible_to_users=False),
    )
    assert response.status_code == 422
    db_session.refresh(place)
    assert place.is_visible_in_catalog is True


def test_legacy_admin_put_still_updates_ordinary_data(client, db_session, published_place_factory) -> None:
    place = published_place_factory(slug="legacy-put-ordinary", title="Старое название")
    response = client.put(
        f"/admin/places/{place.id}",
        json=_ordinary_put_payload(place, title="Новое название"),
    )
    assert response.status_code == 200
    db_session.refresh(place)
    assert place.title == "Новое название"
    assert place.publication_status == "published"
    assert place.is_published is True
