from datetime import time

from models.data_quality import DataQualityIssue
from models.place_photo_candidate import PlacePhotoCandidate
from models.place_schedule import PlaceSchedule


def _set_quality_fields(db_session, place, *, canonical_category=None, short_description=None, opening_hours=None):
    if canonical_category is not None:
        place.canonical_category = canonical_category
    if short_description is not None:
        place.short_description = short_description
    if opening_hours is not None:
        place.opening_hours = opening_hours
    db_session.add(place)
    db_session.commit()
    db_session.refresh(place)
    return place


def test_critical_coverage_excludes_service_places_from_tourist_coverage(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-service-city", name="Critical Service")
    museum = place_factory(
        city_id=city.id,
        category="museum",
        image_url="https://example.com/museum.jpg",
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        museum,
        canonical_category="museum",
        short_description="A complete museum card for tourists.",
        opening_hours={"mon": "10:00-18:00"},
    )
    pharmacy = place_factory(
        city_id=city.id,
        category="pharmacy",
        image_url=None,
        address=None,
    )
    _set_quality_fields(db_session, pharmacy, canonical_category="pharmacy")

    row = client.get(f"/admin/quality?city_slug={city.slug}").json()["items"][0]
    coverage = row["critical_coverage"]

    assert coverage["tourist_places"]["total"] == 1
    assert coverage["tourist_places"]["excluded_non_tourist"] == 1
    assert coverage["coverage"]["has_approved_photo"]["count"] == 1
    assert coverage["coverage"]["has_approved_photo"]["pct"] == 100.0


def test_museum_without_hours_is_route_blocker(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-museum-city", name="Critical Museum")
    place = place_factory(
        city_id=city.id,
        category="museum",
        image_url="https://example.com/museum.jpg",
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="museum",
        short_description="A useful description for a museum.",
    )

    row = client.get(f"/admin/quality?city_slug={city.slug}").json()["items"][0]
    coverage = row["critical_coverage"]

    assert row["route_blockers_total"] == 1
    assert coverage["route_blockers_breakdown"]["missing_opening_hours"] == 1
    assert coverage["city_readiness"]["is_launch_ready"] is False


def test_landmark_without_hours_is_route_ready(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-landmark-city", name="Critical Landmark")
    place = place_factory(
        city_id=city.id,
        category="monument",
        image_url="https://example.com/monument.jpg",
        address=None,
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="monument",
        short_description="A complete landmark description for a walking route.",
    )

    row = client.get(f"/admin/quality?city_slug={city.slug}").json()["items"][0]

    assert row["route_ready_total"] == 1
    assert row["route_blockers_total"] == 0
    assert "missing_opening_hours" not in row["critical_coverage"]["route_blockers_breakdown"]


def test_pending_photo_candidate_requires_photo_review_not_silent_auto_apply(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-photo-city", name="Critical Photo")
    place = place_factory(
        city_id=city.id,
        category="museum",
        image_url=None,
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="museum",
        short_description="A useful description for a museum.",
        opening_hours={"mon": "10:00-18:00"},
    )
    db_session.add(PlacePhotoCandidate(
        place_id=place.id,
        image_url="https://example.com/candidate.jpg",
        source_type="wikimedia",
        source_url="https://example.com/source",
        match_type="name",
        confidence=0.92,
        status="candidate",
    ))
    db_session.commit()

    row = client.get(f"/admin/quality?city_slug={city.slug}").json()["items"][0]
    coverage = row["critical_coverage"]

    assert row["route_ready_total"] == 1
    assert row["card_blockers_total"] == 1
    assert coverage["manual_review_queue"]["pending_photo_review"] == 1
    assert coverage["manual_review_total"] == 1


def test_critical_coverage_city_endpoint_returns_actionable_summary(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-endpoint-city", name="Critical Endpoint")
    place = place_factory(
        city_id=city.id,
        category="museum",
        image_url=None,
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="museum",
        short_description="A useful description for a museum.",
    )

    payload = client.get(f"/admin/data-quality/cities/{city.slug}/critical-coverage").json()

    assert payload["city_slug"] == city.slug
    assert payload["route_blockers_total"] == 1
    assert payload["card_blockers_total"] == 1
    assert payload["route_blockers_breakdown"]["missing_opening_hours"] == 1
    assert payload["coverage"]["has_opening_hours"]["pct"] == 0.0
    assert payload["next_actions"][0]["type"] == "resolve_route_blockers"


def test_critical_coverage_places_endpoint_filters_by_bucket_and_reason(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-drilldown-city", name="Critical Drilldown")
    blocked = place_factory(
        city_id=city.id,
        title="Museum Without Hours",
        category="museum",
        image_url="https://example.com/museum.jpg",
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        blocked,
        canonical_category="museum",
        short_description="A useful description for a museum.",
    )
    ready = place_factory(
        city_id=city.id,
        title="Ready Monument",
        category="monument",
        image_url="https://example.com/monument.jpg",
        address="Square 1",
    )
    _set_quality_fields(
        db_session,
        ready,
        canonical_category="monument",
        short_description="A complete landmark description for a walking route.",
    )

    payload = client.get(
        f"/admin/data-quality/cities/{city.slug}/critical-coverage/places"
        "?bucket=route_blocker&reason=missing_opening_hours"
    ).json()

    assert payload["total"] == 1
    assert payload["items"][0]["place"]["title"] == "Museum Without Hours"
    assert payload["items"][0]["route_status"] == "route_blocker"
    assert payload["items"][0]["route_blockers"][0]["reason"] == "missing_opening_hours"


def test_normalized_schedule_counts_as_hours_coverage(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-schedule-city", name="Critical Schedule")
    place = place_factory(
        city_id=city.id,
        category="museum",
        image_url="https://example.com/museum.jpg",
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="museum",
        short_description="A useful description for a museum.",
    )
    db_session.add(PlaceSchedule(
        place_id=place.id,
        weekday="mon",
        open_time=time(10, 0),
        close_time=time(18, 0),
        is_closed=False,
    ))
    db_session.commit()

    payload = client.get(f"/admin/data-quality/cities/{city.slug}/critical-coverage").json()

    assert payload["route_ready_total"] == 1
    assert payload["coverage"]["has_opening_hours"]["count"] == 1
    assert payload["coverage"]["has_opening_hours"]["pct"] == 100.0


def test_critical_coverage_refresh_materializes_idempotent_state(client, db_session, city_factory, place_factory):
    city = city_factory(slug="critical-materialize-city", name="Critical Materialize")
    place = place_factory(
        city_id=city.id,
        category="museum",
        image_url=None,
        address="Museum street 1",
    )
    _set_quality_fields(
        db_session,
        place,
        canonical_category="museum",
        short_description="A useful description for a museum.",
    )

    first = client.post(f"/admin/data-quality/cities/{city.slug}/critical-coverage/refresh").json()

    assert first["created"] == 1
    assert first["updated"] == 0
    assert first["unchanged"] == 0
    assert first["by_bucket"]["route_blocker"] == 1
    assert first["snapshot"]["created"] == 1

    issues = db_session.query(DataQualityIssue).filter(
        DataQualityIssue.city_id == city.id,
        DataQualityIssue.issue_type == "critical_coverage_state",
        DataQualityIssue.source == "critical_coverage_v2",
    ).all()
    assert len(issues) == 1
    assert issues[0].status == "current"
    assert issues[0].severity == "critical"
    assert issues[0].evidence["bucket"] == "route_blocker"
    assert issues[0].evidence["route_blockers"][0]["reason"] == "missing_opening_hours"

    snapshots = db_session.query(DataQualityIssue).filter(
        DataQualityIssue.city_id == city.id,
        DataQualityIssue.issue_type == "critical_coverage_city_snapshot",
        DataQualityIssue.source == "critical_coverage_v2",
    ).all()
    assert len(snapshots) == 1
    assert snapshots[0].status == "current"
    assert snapshots[0].evidence["by_bucket"]["route_blocker"] == 1
    assert snapshots[0].evidence["summary"]["route_blockers_total"] == 1

    second = client.post(f"/admin/data-quality/cities/{city.slug}/critical-coverage/refresh").json()

    assert second["created"] == 0
    assert second["updated"] == 0
    assert second["unchanged"] == 1
    assert second["snapshot"]["unchanged"] == 1
    assert db_session.query(DataQualityIssue).filter(
        DataQualityIssue.city_id == city.id,
        DataQualityIssue.issue_type == "critical_coverage_state",
        DataQualityIssue.source == "critical_coverage_v2",
    ).count() == 1
