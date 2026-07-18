from __future__ import annotations

from types import SimpleNamespace

from schemas.user_route import UserRouteIntent
from services.user_route_mapper import final_route_to_state


def _intent() -> UserRouteIntent:
    return UserRouteIntent(lat=54.0, lng=20.0)


def _final(status: str):
    return SimpleNamespace(
        route_id="route-status-test",
        status=status,
        partial_reason=None,
        points=[],
        total_places=0,
        total_minutes=0,
        total_estimated_minutes=0,
        estimated_distance=0.0,
        estimated_end_time=None,
        has_warnings=False,
        warning_count=0,
        places_with_warnings=[],
        warnings=[],
        quality_score=0.0,
        quality_status="weak",
        quality_breakdown={},
        total_walk_distance_meters=0,
        time_breakdown={},
        category_distribution={},
        candidate_options=[],
        pipeline_trace=[],
    )


def test_build_mapping_preserves_final_route_status_new() -> None:
    state = final_route_to_state(_final("partial_route"), _intent())

    assert state.status == "partial_route"


def test_mapper_has_no_status_override_contract_new() -> None:
    state = final_route_to_state(_final("no_route"), _intent(), revision=2)

    assert state.status == "no_route"
    assert state.revision == 2
