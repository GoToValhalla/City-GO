from __future__ import annotations

from services.admin_mobile_place_review import list_review_cities, next_review_place, publish_place


def test_moderation_queue_opens_hidden_draft_places(db_session, city_factory, place_factory):
    city = city_factory(slug="arkhangelsk", name="Архангельск")
    place = place_factory(
        city_id=city.id,
        title="Hidden imported draft",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )

    cities = list_review_cities(db_session)
    item = next(item for item in cities["items"] if item["slug"] == "arkhangelsk")
    assert item["needs_review"] == 1

    queue = next_review_place(db_session, "arkhangelsk")

    assert queue["remaining"] == 1
    assert queue["place"]["id"] == place.id


def test_publish_from_moderation_activates_imported_hidden_place(db_session, city_factory, place_factory):
    city = city_factory(slug="almaty", name="Алматы")
    place = place_factory(
        city_id=city.id,
        title="Imported hidden draft",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="needs_review",
    )

    result = publish_place(db_session, place.id, "test-admin")
    db_session.refresh(place)

    assert result["action"] == "published"
    assert place.is_active is True
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_route_eligible is True
    assert place.is_searchable is True
    assert place.publication_status == "published"
