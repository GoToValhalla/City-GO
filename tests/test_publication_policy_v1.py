import allure

from models.place_change_review import PlaceChangeReview
from models.place_publication_decision import PlacePublicationDecision
from models.place_snapshot import PlaceSnapshot
from models.review_queue_item import ReviewQueueItem
from services.publication_policy import (
    DECISION_AUTO_PUBLISH,
    DECISION_HIDDEN,
    DECISION_SHADOW_AUTO_PUBLISH,
    MODE_APPLY,
    MODE_SHADOW,
    REASON_LOW_TRUST,
    REASON_NAME_CHANGE,
    PublicationPolicyConfig,
    apply_publication_decision,
    create_change_review,
    evaluate_new_place,
    run_hard_gates,
)
from services.publication_policy_summary import get_publication_policy_summary


def _make_high_trust(place):
    place.quality_score = 40
    place.image_url = "https://example.test/photo.jpg"
    place.short_description = "A reliable public place description with enough detail for catalog users and routing decisions."
    place.address = "Central Street, 1"
    place.opening_hours = {"daily": "10:00-20:00"}
    place.source = "manual"
    place.source_url = "https://example.test/place"
    place.confidence_score = 9
    place.verification_status = "verified"
    place.existence_confidence_level = "high"
    return place


@allure.title("Публикация: shadow mode не публикует место с высоким доверием")
def test_publication_policy_shadow_keeps_high_trust_place_unpublished(db_session, place_factory):
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    _make_high_trust(place)
    db_session.commit()

    config = PublicationPolicyConfig(mode=MODE_SHADOW, auto_publish_enabled=False, auto_publish_threshold=90)
    decision = evaluate_new_place(place, config=config)
    apply_publication_decision(db_session, place, decision, config=config)
    db_session.commit()
    db_session.refresh(place)

    assert decision.decision == DECISION_SHADOW_AUTO_PUBLISH
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert db_session.query(PlacePublicationDecision).filter_by(place_id=place.id, decision=DECISION_SHADOW_AUTO_PUBLISH).count() == 1


@allure.title("Публикация: apply mode публикует только место с высоким доверием")
def test_publication_policy_apply_publishes_high_trust_place(db_session, place_factory):
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    _make_high_trust(place)
    db_session.commit()

    config = PublicationPolicyConfig(mode=MODE_APPLY, auto_publish_enabled=True, auto_publish_threshold=90)
    decision = evaluate_new_place(place, config=config)
    apply_publication_decision(db_session, place, decision, config=config)
    db_session.commit()
    db_session.refresh(place)

    assert decision.decision == DECISION_AUTO_PUBLISH
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_route_eligible is True
    assert place.publication_status == "published"
    assert db_session.query(PlaceSnapshot).filter_by(place_id=place.id, reason="pre_auto_publish").count() == 1


@allure.title("Публикация: место с generic-названием не проходит hard gate даже при высоком доверии")
def test_publication_policy_blocks_generic_name_even_with_high_trust(db_session, place_factory):
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    _make_high_trust(place)
    place.title = "место для отдыха 134567"
    db_session.commit()

    failed_gates = run_hard_gates(place, city=place.city)

    assert "generic_name_requires_review" in failed_gates

    config = PublicationPolicyConfig(mode=MODE_APPLY, auto_publish_enabled=True, auto_publish_threshold=90)
    decision = evaluate_new_place(place, config=config)
    apply_publication_decision(db_session, place, decision, config=config)
    db_session.commit()
    db_session.refresh(place)

    assert decision.decision != DECISION_AUTO_PUBLISH
    assert place.is_published is False


@allure.title("Публикация: критичное изменение оставляет место видимым и создаёт review")
def test_publication_policy_critical_change_keeps_published_place_visible(db_session, place_factory):
    place = place_factory(title="Old Name", is_published=True, is_visible_in_catalog=True, is_route_eligible=True, is_searchable=True)
    _make_high_trust(place)
    db_session.commit()

    review = create_change_review(db_session, place, field_name="title", old_value="Old Name", new_value="New Name", source="osm_reimport")
    db_session.commit()
    db_session.refresh(place)

    assert review is not None
    assert place.title == "Old Name"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert db_session.query(PlaceChangeReview).filter_by(place_id=place.id, reason=REASON_NAME_CHANGE, status="pending").count() == 1
    assert db_session.query(ReviewQueueItem).filter_by(place_id=place.id, reason=REASON_NAME_CHANGE, status="open").count() == 1


@allure.title("Публикация: summary считает решения, review, trust score и причины")
def test_publication_policy_summary_counts_decisions_reviews_and_reasons(db_session, place_factory):
    place = place_factory(is_published=False, is_visible_in_catalog=False, is_route_eligible=False, is_searchable=False, publication_status="draft")
    _make_high_trust(place)
    low_trust_place = place_factory(
        slug="low-trust-place",
        title="Low Trust Place",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
    )
    low_trust_place.quality_score = 40
    db_session.commit()

    shadow_config = PublicationPolicyConfig(mode=MODE_SHADOW, auto_publish_enabled=False, auto_publish_threshold=90)
    apply_publication_decision(db_session, place, evaluate_new_place(place, config=shadow_config), config=shadow_config)

    apply_config = PublicationPolicyConfig(mode=MODE_APPLY, auto_publish_enabled=True, auto_publish_threshold=90)
    apply_publication_decision(db_session, place, evaluate_new_place(place, config=apply_config), config=apply_config)
    apply_publication_decision(db_session, low_trust_place, evaluate_new_place(low_trust_place, config=apply_config), config=apply_config)
    create_change_review(db_session, place, field_name="title", old_value="Old Name", new_value="New Name", source="osm_reimport")
    db_session.commit()

    summary = get_publication_policy_summary(db_session, days=7)

    assert summary["total_decisions"] == 3
    assert summary["by_decision"][DECISION_SHADOW_AUTO_PUBLISH] == 1
    assert summary["by_decision"][DECISION_AUTO_PUBLISH] == 1
    assert summary["by_decision"][DECISION_HIDDEN] == 1
    assert summary["open_publication_review_items"] >= 1
    assert summary["pending_change_reviews"] == 1
    assert summary["trust_score"]["avg"] is not None
    assert summary["top_review_reasons"][0]["reason"] == REASON_LOW_TRUST
    assert summary["recent_blocked"][0]["title"] == "Low Trust Place"
