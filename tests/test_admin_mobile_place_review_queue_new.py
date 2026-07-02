from __future__ import annotations

from services.admin_mobile_place_review import auto_publish_trusted_places, list_review_cities, next_review_place, publish_place


def test_moderation_queue_does_not_show_auto_backlog_drafts(db_session, city_factory, place_factory):
    city = city_factory(slug="arkhangelsk", name="Архангельск")
    place_factory(
        city_id=city.id,
        title="Auto backlog imported draft",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )

    cities = list_review_cities(db_session)
    queue = next_review_place(db_session, "arkhangelsk")

    assert all(item["slug"] != "arkhangelsk" for item in cities["items"])
    assert queue["remaining"] == 0
    assert queue["place"] is None


def test_moderation_queue_opens_explicit_manual_review_places(db_session, city_factory, place_factory):
    city = city_factory(slug="rostov-on-don", name="Ростов-на-Дону")
    place = place_factory(
        city_id=city.id,
        title="Manual review place",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="needs_review",
    )

    cities = list_review_cities(db_session)
    item = next(item for item in cities["items"] if item["slug"] == "rostov-on-don")
    queue = next_review_place(db_session, "rostov-on-don")

    assert item["needs_review"] == 1
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


def test_trusted_official_address_draft_is_auto_published(db_session, city_factory, place_factory):
    city = city_factory(slug="zelenogradsk-official", name="Зеленоградск")
    place = place_factory(
        city_id=city.id,
        title="Official address place",
        address="ул. Туристическая, 1",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )
    place.address_source = "official_site"
    place.address_confidence = 0.95
    place.quality_score = 75
    db_session.add(place)
    db_session.commit()

    result = auto_publish_trusted_places(db_session, city_slug="zelenogradsk-official")
    db_session.refresh(place)

    assert result["published"] == 1
    assert place.publication_status == "published"
    assert place.is_active is True
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_route_eligible is True
    assert place.is_searchable is True


def test_low_confidence_address_draft_stays_in_auto_backlog(db_session, city_factory, place_factory):
    city = city_factory(slug="low-confidence-city", name="Низкая уверенность")
    place = place_factory(
        city_id=city.id,
        title="Low confidence place",
        address="ул. Спорная, 1",
        is_active=False,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )
    place.address_source = "official_site"
    place.address_confidence = 0.4
    place.quality_score = 75
    db_session.add(place)
    db_session.commit()

    result = auto_publish_trusted_places(db_session, city_slug="low-confidence-city")
    db_session.refresh(place)

    assert result["published"] == 0
    assert place.publication_status == "draft"
    assert place.is_published is False
