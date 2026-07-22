"""Real PostgreSQL coverage for Stage 5 atomic replacement/readiness."""

from unittest.mock import patch

import pytest

from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import ProjectionRebuildJob, RouteCandidateSet, RoutingPlaceNode, SearchPlaceDocument
from services.data_foundation_projection_service import build_snapshot_from_place
from services.projection_readiness_service import assert_projection_ready
from services.routing_projection_rebuild_service import rebuild_route_candidate_sets, rebuild_routing_place_nodes
from services.search_projection_rebuild_service import rebuild_search_place_documents

from conftest import make_published_place


def test_stage5_rebuilds_are_atomic_versioned_and_idempotent_postgres(pg_session, pg_city, pg_category):
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    snapshot = build_snapshot_from_place(place, snapshot_version=1)
    pg_session.add(snapshot); pg_session.commit()
    before = (place.is_published, place.publication_status)
    try:
        first = rebuild_search_place_documents(pg_session, city_id=pg_city.id)
        rebuild_routing_place_nodes(pg_session, city_id=pg_city.id)
        rebuild_route_candidate_sets(pg_session, city_id=pg_city.id)
        pg_session.commit()
        second = rebuild_search_place_documents(pg_session, city_id=pg_city.id)
        pg_session.commit(); pg_session.refresh(place)
        assert first["status"] == second["status"] == "succeeded"
        assert pg_session.query(SearchPlaceDocument).filter_by(city_id=pg_city.id).count() == 1
        assert pg_session.query(RoutingPlaceNode).filter_by(city_id=pg_city.id).count() == 1
        assert pg_session.query(RouteCandidateSet).filter_by(city_id=pg_city.id).one().candidate_count == 1
        assert_projection_ready(pg_session, projection_type="search_place_document", city_id=pg_city.id)
        assert_projection_ready(pg_session, projection_type="routing_place_node", city_id=pg_city.id)
        assert (place.is_published, place.publication_status) == before
    finally:
        pg_session.rollback()
        pg_session.query(RouteCandidateSet).filter_by(city_id=pg_city.id).delete()
        pg_session.query(RoutingPlaceNode).filter_by(city_id=pg_city.id).delete()
        pg_session.query(SearchPlaceDocument).filter_by(city_id=pg_city.id).delete()
        pg_session.query(ProjectionRebuildJob).filter_by(city_id=pg_city.id).delete()
        pg_session.query(PublishedPlaceSnapshot).filter_by(city_id=pg_city.id).delete()
        pg_session.commit()


def test_failed_search_replacement_rolls_back_to_last_generation_postgres(pg_session, pg_city, pg_category):
    place = make_published_place(pg_session, city=pg_city, category=pg_category)
    pg_session.add(build_snapshot_from_place(place, snapshot_version=1))
    pg_session.commit()
    rebuild_search_place_documents(pg_session, city_id=pg_city.id)
    pg_session.commit()
    original = pg_session.query(SearchPlaceDocument).filter_by(place_id=place.id).one()
    original_id, original_version = original.id, original.source_snapshot_version
    pg_session.add(build_snapshot_from_place(place, snapshot_version=2))
    pg_session.commit()

    with patch.object(pg_session, "add_all", side_effect=RuntimeError("injected backfill failure")):
        with pytest.raises(RuntimeError, match="injected backfill failure"):
            rebuild_search_place_documents(pg_session, city_id=pg_city.id)
    pg_session.rollback()

    preserved = pg_session.query(SearchPlaceDocument).filter_by(place_id=place.id).one()
    assert (preserved.id, preserved.source_snapshot_version) == (original_id, original_version)
    pg_session.query(SearchPlaceDocument).filter_by(city_id=pg_city.id).delete()
    pg_session.query(ProjectionRebuildJob).filter_by(city_id=pg_city.id).delete()
    pg_session.query(PublishedPlaceSnapshot).filter_by(city_id=pg_city.id).delete()
    pg_session.commit()
