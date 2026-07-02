from __future__ import annotations

from services.admin_mobile_place_review import list_review_cities, next_review_place, publish_place
from tests.allure_support import title


@title("Telegram moderation не показывает draft и auto backlog как ручную очередь")
def test_mobile_review_queue_ignores_draft_and_auto_backlog(
    db_session,
    city_factory,
    draft_place_factory,
    auto_backlog_place_factory,
) -> None:
    city = city_factory(slug="queue-auto-only", name="Auto Only")
    draft_place_factory(city_id=city.id, slug="draft-only")
    auto_backlog_place_factory(city_id=city.id, slug="auto-only")

    cities = list_review_cities(db_session)
    next_item = next_review_place(db_session, city.slug)

    assert cities == {"items": [], "total": 0}
    assert next_item["remaining"] == 0
    assert next_item["place"] is None


@title("Telegram moderation показывает только явные manual-review статусы")
def test_mobile_review_queue_lists_only_manual_statuses(
    db_session,
    city_factory,
    manual_review_place_factory,
    auto_backlog_place_factory,
) -> None:
    city = city_factory(slug="queue-manual", name="Manual Queue")
    manual = manual_review_place_factory(city_id=city.id, slug="manual-one")
    auto_backlog_place_factory(city_id=city.id, slug="auto-hidden-from-manual")

    cities = list_review_cities(db_session)
    next_item = next_review_place(db_session, city.slug)

    assert cities["total"] == 1
    assert cities["items"][0]["slug"] == city.slug
    assert cities["items"][0]["needs_review"] == 1
    assert cities["items"][0]["auto_backlog"] == 1
    assert next_item["remaining"] == 1
    assert next_item["place"]["id"] == manual.id


@title("Publish из moderation выставляет полный public state")
def test_moderation_publish_sets_complete_public_state(db_session, manual_review_place_factory) -> None:
    place = manual_review_place_factory(
        slug="manual-publishable",
        address="ул. Мира, 1",
        category="museum",
    )

    result = publish_place(db_session, place.id, actor="test-admin")
    published = result["place"]

    assert result["action"] == "published"
    assert published["is_active"] is True
    assert published["is_published"] is True
    assert published["is_visible_in_catalog"] is True
    assert published["is_searchable"] is True
    assert published["is_route_eligible"] is True
    assert published["publication_status"] == "published"
    assert published["verification_status"] == "trusted"
