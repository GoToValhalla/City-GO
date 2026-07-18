from __future__ import annotations

from models.place_publication_transition import PlacePublicationTransition
from services.admin_mobile_place_review import (
    defer_place,
    list_review_cities,
    next_review_place,
    publish_place,
    reject_place,
    restore_place,
)
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


@title("Publish из moderation выставляет полный public state и ledger")
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
    db_session.refresh(place)
    assert place.publication_reason_code is None
    transition = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .order_by(PlacePublicationTransition.id.desc())
        .first()
    )
    assert transition is not None
    assert transition.to_status == "published"
    assert transition.reason_code == "published"
    assert transition.source == "mobile_review"


@title("Reject из moderation записывает admin_reject")
def test_moderation_reject_uses_canonical_writer(db_session, manual_review_place_factory) -> None:
    place = manual_review_place_factory(slug="manual-rejectable", category="museum")

    result = reject_place(db_session, place.id, actor="test-admin")

    assert result["action"] == "rejected"
    db_session.refresh(place)
    assert place.publication_status == "rejected"
    assert place.publication_reason_code == "admin_reject"
    transition = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id == place.id)
        .order_by(PlacePublicationTransition.id.desc())
        .first()
    )
    assert transition is not None
    assert transition.to_status == "rejected"
    assert transition.reason_code == "admin_reject"
    assert transition.source == "mobile_review"


@title("Defer и restore из moderation сохраняют разные reason codes")
def test_moderation_queue_actions_use_structured_reasons(db_session, manual_review_place_factory) -> None:
    deferred = manual_review_place_factory(slug="manual-defer", category="museum")
    restored = manual_review_place_factory(slug="manual-restore", category="museum")

    defer_place(db_session, deferred.id, actor="test-admin")
    restore_place(db_session, restored.id, actor="test-admin")

    db_session.refresh(deferred)
    db_session.refresh(restored)
    assert deferred.publication_status == "needs_review"
    assert deferred.publication_reason_code == "admin_defer"
    assert restored.publication_status == "needs_review"
    assert restored.publication_reason_code == "needs_manual_review"
    transitions = (
        db_session.query(PlacePublicationTransition)
        .filter(PlacePublicationTransition.place_id.in_((deferred.id, restored.id)))
        .all()
    )
    by_place = {item.place_id: item for item in transitions}
    assert by_place[deferred.id].reason_code == "admin_defer"
    assert by_place[restored.id].reason_code == "needs_manual_review"
