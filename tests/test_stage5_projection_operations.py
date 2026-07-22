from types import SimpleNamespace

import pytest

from models.search_routing_stage5 import ProjectionRebuildJob, RouteCandidateSet, RoutingPlaceNode, SearchPlaceDocument
from services.data_foundation_projection_service import build_snapshot_from_place
from services.feature_toggle_service import update_toggle
from services.projection_readiness_service import assert_projection_ready, projection_readiness
from services.public_read_projection_service import PublicReadProjectionError, REASON_EMPTY, REASON_FAILED
from services.routing_projection_candidate_service import routing_projection_candidates
from services.routing_projection_rebuild_service import rebuild_route_candidate_sets, rebuild_routing_place_nodes
from services.search_projection_rebuild_service import rebuild_search_place_documents
from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.user_route_place_loader import load_ordered_places


def _snapshot(db, place, version=1):
    row = build_snapshot_from_place(place, snapshot_version=version)
    db.add(row); db.commit(); return row


def test_city_rebuilds_are_idempotent_and_do_not_mutate_publication(db_session, place_factory):
    place = place_factory(slug="stage5", title="Stage 5")
    before = (place.is_published, place.is_route_eligible, place.publication_status)
    _snapshot(db_session, place)
    first = rebuild_search_place_documents(db_session, city_id=place.city_id)
    second = rebuild_search_place_documents(db_session, city_id=place.city_id)
    db_session.commit(); db_session.refresh(place)
    assert first["status"] == second["status"] == "succeeded"
    assert db_session.query(SearchPlaceDocument).count() == 1
    assert (place.is_published, place.is_route_eligible, place.publication_status) == before


def test_global_empty_rebuild_fails_closed(db_session):
    result = rebuild_search_place_documents(db_session)
    db_session.commit()
    assert result["rebuilt_count"] == 0
    status = projection_readiness(db_session, projection_type="search_place_document", city_id=None)
    assert status.ready is False
    assert status.reason == REASON_EMPTY


def test_routing_rebuild_and_candidate_set_are_projection_only(db_session, place_factory):
    place = place_factory(slug="route-node", title="Route Node", lat=54.9, lng=20.3)
    _snapshot(db_session, place)
    assert rebuild_routing_place_nodes(db_session)["status"] == "succeeded"
    result = rebuild_route_candidate_sets(db_session)
    assert result["status"] == "succeeded"
    assert result["expected_count"] == result["actual_count"] == 1
    assert result["generation"] and result["is_complete"] is True
    db_session.commit()
    readiness = projection_readiness(db_session, projection_type="route_candidate_set", city_id=None)
    assert readiness.expected_count == readiness.actual_count == 1
    update_toggle(db_session, key="routing_projection_reads_enabled", scope="global", scope_id=None, value_bool=True, actor="test")
    ctx = SimpleNamespace(city_id="zelenogradsk", location=(54.9, 20.3), radius_meters=10_000,
                          avoided_place_ids=[], avoided_categories=[], destination_id=None)
    assert [row.id for row in routing_projection_candidates(db_session, ctx)] == [place.id]


def test_running_duplicate_is_skipped_without_replacement(db_session, place_factory):
    place = place_factory(slug="duplicate-job")
    _snapshot(db_session, place)
    job = ProjectionRebuildJob(projection_type="routing_place_node", city_id=place.city_id,
                               scope_key=f"city:{place.city_id}", status="running")
    db_session.add(job); db_session.commit()
    result = rebuild_routing_place_nodes(db_session, city_id=place.city_id)
    assert result["status"] == "skipped"
    assert db_session.query(RoutingPlaceNode).count() == 0


def test_failed_new_routing_generation_preserves_last_rows(db_session, place_factory):
    place = place_factory(slug="preserved", lat=54.9, lng=20.3)
    _snapshot(db_session, place)
    rebuild_routing_place_nodes(db_session, city_id=place.city_id); db_session.commit()
    newer = build_snapshot_from_place(place, snapshot_version=2)
    newer.snapshot_payload = dict(newer.snapshot_payload) | {"lat": None}
    db_session.add(newer); db_session.commit()
    result = rebuild_routing_place_nodes(db_session, city_id=place.city_id); db_session.commit()
    assert result["status"] == "failed"
    assert db_session.query(RoutingPlaceNode).count() == 1
    assert projection_readiness(db_session, projection_type="routing_place_node", city_id=place.city_id).reason == REASON_FAILED


def test_unsafe_activation_is_rejected(db_session, place_factory):
    _snapshot(db_session, place_factory(slug="unsafe"))
    with pytest.raises(PublicReadProjectionError):
        update_toggle(db_session, key="catalog_projection_reads_enabled", scope="global", scope_id=None, value_bool=True, actor="test")


def test_route_session_continuation_uses_projection_places(db_session, place_factory):
    place = place_factory(slug="session-projection", title="Projected Session Place")
    _snapshot(db_session, place)
    rebuild_routing_place_nodes(db_session)
    rebuild_route_candidate_sets(db_session)
    db_session.commit()
    update_toggle(db_session, key="routing_projection_reads_enabled", scope="global", scope_id=None, value_bool=True, actor="test")
    place.title = "Write Side Changed"
    db_session.commit()
    route = UserRouteState(
        route_id="route",
        context=UserRouteIntent(lat=54.9, lng=20.3, city_id="zelenogradsk"),
        points=[UserRoutePoint(place_id=str(place.id), position=1, lat=54.9, lng=20.3, category="place", visit_minutes=20)],
        total_places=1, total_minutes=20, total_estimated_minutes=20,
        estimated_distance=0, has_warnings=False, warning_count=0,
    )
    assert load_ordered_places(db_session, route)[0].title == "Projected Session Place"
