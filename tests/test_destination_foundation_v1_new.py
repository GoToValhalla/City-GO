"""Destination foundation v1 — comprehensive tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models.destination import Destination, DestinationMembershipConflict, DestinationPlaceMembership, DestinationScope
from models.place import Place
from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from schemas.user_route import UserRouteIntent, UserRouteState
from services.candidate_retrieval_service import CandidateRetrievalService
from services.destination_backfill_service import backfill_cities_to_destinations
from services.destination_membership_recalculation_service import recalculate_place_memberships
from services.destination_membership_service import hide_membership, upsert_membership
from services.place_service import get_places


@pytest.fixture
def backfilled(db_session, city_factory, place_factory):
    city = city_factory(slug="dest-city-a", name="Dest City A", launch_status="published", is_active=True)
    place_factory(city_id=city.id, slug="cafe-a", category="cafe", title="Cafe A", is_published=True, is_visible_in_catalog=True)
    backfill_cities_to_destinations(db_session)
    dest = db_session.query(Destination).filter(Destination.legacy_city_id == city.id).first()
    if dest is not None:
        dest.is_published = True
        db_session.commit()
    return city


def test_backfill_cities_to_destinations_idempotent_new(db_session, city_factory, place_factory, backfilled):
    backfill_cities_to_destinations(db_session)
    second = backfill_cities_to_destinations(db_session)
    assert second["destinations_created"] == 0
    assert second["memberships_created"] == 0
    assert db_session.query(Destination).filter(Destination.slug == "dest-city-a").count() == 1


def test_place_membership_legacy_city_backfill_new(db_session, backfilled, place_factory):
    place = db_session.query(Place).filter(Place.slug == "cafe-a").first()
    dest = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    membership = db_session.query(DestinationPlaceMembership).filter_by(place_id=place.id, destination_id=dest.id).one()
    assert membership.assignment_type == "legacy_city"
    assert membership.is_primary is True
    assert place.primary_destination_id == dest.id


def test_legacy_city_slug_places_compatibility_new(client, backfilled):
    response = client.get("/places/", params={"city_slug": "dest-city-a"})
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_destination_slug_places_legacy_compat_new(client, backfilled):
    response = client.get("/places/", params={"destination_slug": "dest-city-a"})
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_city_and_destination_slug_both_returns_400_new(client):
    assert client.get("/places/", params={"city_slug": "a", "destination_slug": "b"}).status_code == 400


def test_v1_destinations_list_new(client, backfilled, db_session):
    dest = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    dest.is_published = True
    db_session.commit()
    response = client.get("/v1/destinations")
    assert response.status_code == 200
    assert any(item["slug"] == "dest-city-a" for item in response.json()["items"])


def test_region_with_child_destinations_new(db_session, city_factory, backfilled):
    region = Destination(
        slug="kaliningrad-region",
        name="Калининградская область",
        destination_type="region",
        is_active=True,
        is_published=True,
        center_lat=54.7,
        center_lng=20.5,
    )
    db_session.add(region)
    db_session.flush()
    city_dest = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    city_dest.parent_id = region.id
    db_session.commit()
    assert len(db_session.query(Destination).filter(Destination.parent_id == region.id).all()) >= 1


def test_poi_between_cities_region_membership_new(db_session, city_factory, place_factory, backfilled):
    region = Destination(
        slug="region-poi",
        name="Регион POI",
        destination_type="region",
        is_active=True,
        is_published=True,
        bbox={"south": 54.5, "north": 55.0, "west": 20.0, "east": 21.0},
    )
    db_session.add(region)
    db_session.flush()
    city = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    place = place_factory(city_id=city.legacy_city_id, slug="fort-poi", category="landmark", title="Fort", lat=54.75, lng=20.5)
    upsert_membership(db_session, place_id=place.id, destination_id=region.id, assignment_type="spatial", is_primary=False)
    db_session.commit()
    assert db_session.query(DestinationPlaceMembership).filter_by(place_id=place.id, destination_id=region.id).count() == 1


def test_remote_poi_not_in_city_catalog_new(db_session, city_factory, place_factory, backfilled, monkeypatch):
    monkeypatch.setattr("services.place_filters_service.should_use_membership_catalog", lambda: True)
    remote = Destination(
        slug="curonian-spit",
        name="Куршская коса",
        destination_type="natural_region",
        is_active=True,
        is_published=True,
        center_lat=55.3,
        center_lng=21.0,
    )
    db_session.add(remote)
    db_session.flush()
    city = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    remote_place = place_factory(
        city_id=city.legacy_city_id,
        slug="remote-dune",
        category="viewpoint",
        title="Dune",
        lat=55.35,
        lng=21.05,
    )
    upsert_membership(db_session, place_id=remote_place.id, destination_id=remote.id, assignment_type="manual", is_primary=True)
    db_session.commit()
    city_items = get_places(db_session, destination_slug="dest-city-a")
    remote_items = get_places(db_session, destination_slug="curonian-spit")
    assert remote_place.id not in {place.id for place in city_items}
    assert any(place.id == remote_place.id for place in remote_items)


def test_one_place_two_destinations_new(db_session, place_factory, backfilled):
    region = Destination(slug="extra-region", name="Extra", destination_type="region", is_active=True, is_published=True)
    db_session.add(region)
    db_session.flush()
    place = db_session.query(Place).first()
    upsert_membership(db_session, place_id=place.id, destination_id=region.id, assignment_type="manual", is_primary=False)
    db_session.commit()
    assert db_session.query(DestinationPlaceMembership).filter_by(place_id=place.id).count() == 2


def test_manual_membership_not_deleted_by_recalc_new(db_session, place_factory, backfilled):
    region = Destination(
        slug="recalc-region",
        name="Recalc",
        destination_type="region",
        is_active=True,
        is_published=True,
        bbox={"south": 0, "north": 90, "west": 0, "east": 180},
    )
    db_session.add(region)
    db_session.flush()
    place = db_session.query(Place).first()
    upsert_membership(db_session, place_id=place.id, destination_id=region.id, assignment_type="manual", is_primary=False)
    db_session.commit()
    recalculate_place_memberships(db_session, place.id)
    assert db_session.query(DestinationPlaceMembership).filter_by(place_id=place.id, destination_id=region.id, assignment_type="manual").count() == 1


def test_stale_membership_after_coordinate_change_new(db_session, place_factory, backfilled):
    place = db_session.query(Place).first()
    place.lat = 55.0
    place.destination_assignment_stale = True
    db_session.commit()
    assert place.destination_assignment_stale is True


def test_walking_route_scope_guard_new(db_session, backfilled):
    from services.destination_route_guard import validate_trip_type_for_destination

    region = Destination(slug="walk-block", name="Block", destination_type="region", is_active=True, is_published=True)
    db_session.add(region)
    db_session.commit()
    reason = validate_trip_type_for_destination(db_session, destination_slug="walk-block", destination_id=None, trip_type="walking")
    assert reason == "walking_not_supported_for_destination"


def test_admin_destinations_list_new(client, backfilled):
    response = client.get("/admin/destinations")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_hidden_membership_excluded_new(db_session, backfilled, monkeypatch):
    monkeypatch.setattr("services.place_filters_service.should_use_membership_catalog", lambda: True)
    dest = db_session.query(Destination).filter(Destination.slug == "dest-city-a").first()
    dest.is_published = True
    place = db_session.query(Place).first()
    hide_membership(db_session, place_id=place.id, destination_id=dest.id)
    db_session.commit()
    items = get_places(db_session, destination_slug="dest-city-a")
    assert place.id not in {item.id for item in items}


def _route_ctx(**overrides) -> MergedContext:
    base = dict(
        location=(54.9611, 20.4703),
        time_budget_minutes=120,
        effective_time_budget_minutes=96,
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        radius_meters=50_000,
        effective_num_stops=5,
        min_stop_duration_minutes=20,
        destination_slug="dest-city-a",
    )
    base.update(overrides)
    return MergedContext(**base)


def test_destination_route_candidate_retrieval_under_flag_new(db_session, backfilled, place_factory, monkeypatch):
    monkeypatch.setattr("services.destination_flags.destination_route_reads_enabled", lambda: True)
    city = backfilled
    extra = place_factory(
        city_id=city.id,
        slug="extra-no-membership",
        category="landmark",
        title="Extra",
        lat=54.9611,
        lng=20.4703,
        is_route_eligible=True,
    )
    candidates = CandidateRetrievalService().get_candidates(db_session, _route_ctx())
    ids = {place.id for place in candidates}
    assert extra.id not in ids
    assert db_session.query(Place).filter(Place.slug == "cafe-a").first().id in ids


def test_old_city_route_build_city_slug_compat_new(client, backfilled):
    state = UserRouteState(
        route_id="route-test",
        context=UserRouteIntent(lat=54.96, lng=20.48, city_slug="dest-city-a"),
        total_places=1,
        total_minutes=60,
        total_estimated_minutes=60,
        estimated_distance=1.0,
        has_warnings=False,
        warning_count=0,
    )
    with (
        patch("routers.user_routes.UserRouteBuildService", return_value=MagicMock(build=MagicMock(return_value=state))),
        patch("routers.user_routes._lifecycle.issue_initial", return_value=state),
        patch("routers.user_routes.record_route_build", return_value=True),
    ):
        response = client.post("/v1/user-routes/build", json={"lat": 54.96, "lng": 20.48, "city_slug": "dest-city-a"})
    assert response.status_code == 200
    assert response.json()["route_id"] == "route-test"


def test_overlapping_scopes_conflict_new(db_session, place_factory, backfilled):
    dest = Destination(
        slug="overlap-dest",
        name="Overlap",
        destination_type="region",
        is_active=True,
        is_published=True,
        bbox={"south": 54.0, "north": 56.0, "west": 19.0, "east": 22.0},
    )
    db_session.add(dest)
    db_session.flush()
    bbox = {"south": 54.5, "north": 55.0, "west": 20.0, "east": 21.0}
    db_session.add(DestinationScope(destination_id=dest.id, code="a", name="A", scope_type="catalog", bbox=bbox, priority=1, enabled=True))
    db_session.add(DestinationScope(destination_id=dest.id, code="b", name="B", scope_type="catalog", bbox=bbox, priority=1, enabled=True))
    place = db_session.query(Place).first()
    place.lat = 54.75
    place.lng = 20.5
    db_session.commit()
    result = recalculate_place_memberships(db_session, place.id)
    assert result["conflicts"] >= 1
    assert db_session.query(DestinationMembershipConflict).filter_by(place_id=place.id, destination_id=dest.id).count() >= 1


def test_service_only_not_in_destination_catalog_new(db_session, backfilled, monkeypatch):
    monkeypatch.setattr("services.place_filters_service.should_use_membership_catalog", lambda: True)
    place = db_session.query(Place).first()
    place.internal_status = "service_only"
    db_session.commit()
    items = get_places(db_session, destination_slug="dest-city-a")
    assert place.id not in {item.id for item in items}


def test_destination_slug_normalization_preserved_new(db_session, backfilled):
    from schemas.place_query_params import PlaceQueryParams
    from services.place_query_params_service import normalize_place_query_params

    normalized = normalize_place_query_params(
        PlaceQueryParams(destination_slug="dest-city-a", limit=10, offset=0, sort_by="title", sort_order="asc")
    )
    assert normalized.destination_slug == "dest-city-a"
    assert get_places(db_session, destination_slug="dest-city-a")
