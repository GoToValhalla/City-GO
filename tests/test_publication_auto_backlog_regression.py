from __future__ import annotations

from services.admin_mobile_place_review import auto_publish_trusted_places, is_trusted_auto_publish_candidate, list_review_cities
from tests.allure_support import title


@title("Trusted official draft auto-publishes without requiring photo")
def test_trusted_official_draft_auto_publishes_without_photo(
    db_session,
    city_factory,
    draft_place_factory,
) -> None:
    city = city_factory(slug="trusted-autopublish", name="Trusted")
    place = draft_place_factory(
        city_id=city.id,
        slug="trusted-no-photo",
        category="museum",
        address="Официальный адрес, 1",
        image_url=None,
    )
    place.address_source = "official_site"
    place.address_confidence = 0.95
    place.quality_score = 80
    place.tourist_eligible = True
    db_session.add(place)
    db_session.commit()

    assert is_trusted_auto_publish_candidate(place) is True
    result = auto_publish_trusted_places(db_session, city_slug=city.slug, limit=10, actor="test-policy")
    db_session.refresh(place)

    assert result["checked"] == 1
    assert result["published"] == 1
    assert result["skipped"] == 0
    assert place.publication_status == "published"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True


@title("Low confidence без trusted address остаётся auto backlog и не попадает в manual")
def test_low_confidence_stays_auto_backlog_not_manual_queue(
    db_session,
    city_factory,
    auto_backlog_place_factory,
) -> None:
    city = city_factory(slug="low-confidence", name="Low Confidence")
    place = auto_backlog_place_factory(city_id=city.id, slug="low-confidence-place", address=None)
    place.quality_score = 30
    place.address_confidence = 0.0
    place.address_source = None
    db_session.add(place)
    db_session.commit()

    result = auto_publish_trusted_places(db_session, city_slug=city.slug, limit=10, actor="test-policy")
    queue = list_review_cities(db_session)
    db_session.refresh(place)

    assert result["checked"] == 1
    assert result["published"] == 0
    assert result["skipped"] == 1
    assert place.publication_status == "auto_backlog"
    assert queue == {"items": [], "total": 0}


@title("Duplicate suspected auto backlog не публикуется автоматически")
def test_duplicate_suspected_auto_backlog_is_not_auto_published(
    db_session,
    city_factory,
    auto_backlog_place_factory,
) -> None:
    city = city_factory(slug="duplicate-city", name="Duplicate City")
    place = auto_backlog_place_factory(
        city_id=city.id,
        slug="duplicate-place",
        address="ул. Дубль, 1",
        category="museum",
    )
    place.address_source = "official"
    place.address_confidence = 0.99
    place.quality_score = 95
    place.is_duplicate_suspected = True
    db_session.add(place)
    db_session.commit()

    assert is_trusted_auto_publish_candidate(place) is False
    result = auto_publish_trusted_places(db_session, city_slug=city.slug, limit=10, actor="test-policy")
    db_session.refresh(place)

    assert result["published"] == 0
    assert place.publication_status == "auto_backlog"
    assert place.is_published is False
