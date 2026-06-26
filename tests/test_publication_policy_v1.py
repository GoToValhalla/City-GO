import allure

from models.place_change_review import PlaceChangeReview
from models.place_publication_decision import PlacePublicationDecision
from models.place_snapshot import PlaceSnapshot
from models.review_queue_item import ReviewQueueItem
from services.publication_policy import (
    DECISION_AUTO_PUBLISH,
    DECISION_SHADOW_AUTO_PUBLISH,
    MODE_APPLY,
    MODE_SHADOW,
    REASON_NAME_CHANGE,
    PublicationPolicyConfig,
    apply_publication_decision,
    create_change_review,
    evaluate_new_place,
)


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


@allure.title("Publication policy: shadow keeps high-trust place unpublished")
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


@allure.title("Publication policy: apply publishes only high-trust places")
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


@allure.title("Publication policy: critical change keeps published place visible and creates review")
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
