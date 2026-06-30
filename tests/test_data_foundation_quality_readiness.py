from datetime import datetime, timedelta

from models.admin_operation import AdminOperation
from models.city import City
from models.data_foundation import CityQualitySnapshot, QualityScoreHistory
from services.city_readiness import recalculate_city_readiness_snapshot
from services.quality_scoring import apply_place_quality_score, score_place_quality
from services.route_eligibility import apply_route_eligible_filters, evaluate_place_route_eligibility


def _long_description() -> str:
    return "Городское место с понятной локацией, описанием и пригодностью для маршрутов City Go."


def _complete_place(place) -> None:
    place.canonical_category = "park"
    place.image_url = "https://example.test/place.jpg"
    place.short_description = _long_description()
    place.opening_hours = {"mon": [{"from": "09:00", "to": "21:00"}]}
    place.average_visit_duration_minutes = 45
    place.confidence = 0.95
    place.verified_at = datetime.utcnow()


def test_quality_scoring_promotes_complete_place_to_gold_and_route_eligible(db_session, place_factory):
    place = place_factory(category="park", address="Курортный проспект, 1", price_level=1, indoor=False, outdoor=True)
    _complete_place(place)

    result = apply_place_quality_score(db_session, place, reason="test_quality_scoring")
    db_session.commit()
    db_session.refresh(place)

    assert result.quality_tier == "gold"
    assert result.quality_score >= 80
    assert result.route_eligible is True
    assert place.quality_tier == "gold"
    assert place.is_route_eligible is True
    assert place.route_exclusion_reason is None
    assert db_session.query(QualityScoreHistory).filter(QualityScoreHistory.place_id == place.id).count() == 1


def test_quality_scoring_downgrades_sparse_place_and_blocks_routes(db_session, place_factory):
    place = place_factory(category="museum", address=None)
    place.canonical_category = "museum"
    place.image_url = None
    place.short_description = None
    place.opening_hours = None
    place.average_visit_duration_minutes = None
    place.confidence = None
    place.verified_at = datetime.utcnow() - timedelta(days=500)

    result = apply_place_quality_score(db_session, place, reason="test_sparse_quality")
    db_session.commit()

    assert result.quality_tier in {"draft", "bronze"}
    assert result.route_eligible is False
    assert "quality_tier_not_route_allowed" in ",".join(result.route_eligibility_reasons)


def test_quality_scoring_rejects_bad_poi_even_when_other_fields_are_complete(place_factory):
    place = place_factory(category="viewpoint", address="Набережная, 10", outdoor=True)
    _complete_place(place)
    place.is_spam_poi = True

    result = score_place_quality(place)

    assert result.quality_tier == "rejected"
    assert result.route_eligible is False
    assert "spam_poi" in result.route_eligibility_reasons


def test_route_eligible_filters_match_projected_quality_score(db_session, place_factory):
    eligible_place = place_factory(category="park", address="Ленина, 1", outdoor=True)
    _complete_place(eligible_place)
    apply_place_quality_score(db_session, eligible_place, reason="test_eligible")

    blocked_place = place_factory(category="parking", address="Парковка", outdoor=True)
    blocked_place.canonical_category = "parking"
    blocked_place.image_url = "https://example.test/blocked.jpg"
    blocked_place.short_description = _long_description()
    blocked_place.confidence = 0.95
    blocked_place.verified_at = datetime.utcnow()
    apply_place_quality_score(db_session, blocked_place, reason="test_forbidden")
    db_session.commit()

    eligible_ids = {place.id for place in apply_route_eligible_filters(db_session.query(type(eligible_place))).all()}

    assert eligible_place.id in eligible_ids
    assert blocked_place.id not in eligible_ids
    assert evaluate_place_route_eligibility(blocked_place).eligible is False


def test_city_readiness_recalculation_persists_snapshot_and_city_fields(db_session, city_factory, place_factory):
    city = city_factory(slug="readiness-city", name="Readiness City")
    for index in range(35):
        place = place_factory(slug=f"ready-place-{index}", city_id=city.id, category="park", address=f"Address {index}", price_level=1, outdoor=True)
        _complete_place(place)

    payload = recalculate_city_readiness_snapshot(db_session, city_slug=city.slug, reason="test_city_readiness", recalculate_place_scores=True)

    assert payload is not None
    assert payload["snapshot_id"] is not None
    assert payload["components"]["eligible_places"] == 35
    assert payload["readiness_score"] >= 70
    assert payload["status"] == "ready"

    snapshot = db_session.query(CityQualitySnapshot).filter(CityQualitySnapshot.city_id == city.id).one()
    stored_city = db_session.query(City).filter(City.id == city.id).one()
    assert snapshot.total_places_route_eligible == 35
    assert stored_city.readiness_score == payload["readiness_score"]
    assert stored_city.quality_status == "ready"


def test_admin_recalculate_city_readiness_endpoint_queues_background_job(client, db_session, city_factory, place_factory):
    city = city_factory(slug="admin-readiness", name="Admin Readiness")
    place = place_factory(city_id=city.id, category="park", address="Admin Address", outdoor=True)
    _complete_place(place)
    db_session.commit()

    response = client.post(f"/admin/routes/readiness/{city.slug}/recalculate", json={"reason": "test_admin_endpoint"})

    assert response.status_code == 200
    body = response.json()
    assert body["operation_id"] is not None
    assert body["operation_type"] == "city_readiness_recalculate"
    assert body["city_slug"] == city.slug
    assert body["status"] in {"queued", "running", "completed"}
    assert db_session.query(AdminOperation).filter(AdminOperation.id == body["operation_id"]).count() == 1
