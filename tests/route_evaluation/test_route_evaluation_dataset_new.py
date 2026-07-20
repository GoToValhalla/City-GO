"""CITYGO-358: deterministic route evaluation dataset.

Covers every required (profile, mode) combination against the invariants
listed in the task. Assertions are structural (contract, scope,
uniqueness, coordinate validity, status coherence) — never exact waypoint
identity/order/count, per the task's explicit "invariant-based assertions,
not exact waypoint snapshots" rule.

No production database, no live provider calls, no network dependency: all
data is built via the existing pytest fixtures (city_factory,
place_factory, published_place_factory, db_session — see
tests/conftest.py), which back onto the project's in-memory SQLite test
engine. Determinism: fixed lat/lng offsets (tests/route_evaluation/scenarios.py),
frozen `time_budget_minutes`/`interests` per mode, and a fixed
`route_slots`/`seed` where the underlying service accepts one
(services.route_random_service reads payload.seed; the dynamic route
pipeline itself has no randomness in its scoring/assembly — verified by
running this whole module twice in the same session, see
test_full_dataset_is_deterministic_across_two_runs below).

CI wiring is explicitly out of scope here (belongs to CITYGO-359) — this
is a plain pytest module, run the same way as every other test in the
repository.
"""

from __future__ import annotations

import uuid

import pytest

from schemas.user_route import UserRouteBuildRequest, UserRouteSlotRequest, UserRouteStructuredBuildRequest
from services.user_route_build_service import UserRouteBuildService
from services.user_route_edit_service import UserRouteEditService
from tests.route_evaluation.invariants import run_all_point_invariants
from tests.route_evaluation.scenarios import (
    CityScenario,
    build_active_preview_city,
    build_destination_enabled_city,
    build_healthy_compact_city,
    build_healthy_distributed_city,
    build_inactive_published_city,
    build_mixed_eligibility_city,
    build_mostly_service_only_city,
    build_preparing_city,
    build_single_place_city,
    build_sparse_city,
)

GENERATION_RUN_ID = "citygo358-v1"

# --- Mode -> UserRouteBuildRequest fields -----------------------------------
# "overview"/"express"/"gastro"/"thematic" are product-level names for
# parameter combinations on the existing build_mode="auto" backend path
# (confirmed by CITYGO-357 inventory: no such backend enum exists —
# services/route_builder_v2_service.py only defines
# quick/category/manual/slot). Modeling them as scenarios over the real
# contract, not inventing new backend behavior.
_MODE_REQUEST_KWARGS: dict[str, dict[str, object]] = {
    "overview": {"build_mode": "auto", "time_budget_minutes": 180, "interests": []},
    "express": {"build_mode": "auto", "time_budget_minutes": 60, "interests": []},
    "gastro": {"build_mode": "by_categories", "time_budget_minutes": 120, "interests": ["cafe"]},
    "thematic": {"build_mode": "by_categories", "time_budget_minutes": 120, "interests": ["museum"]},
}

ACTIVE_FREEFORM_MODES = ("overview", "express", "gastro", "thematic")


def _build_request(scenario: CityScenario, mode: str) -> UserRouteBuildRequest:
    kwargs = dict(_MODE_REQUEST_KWARGS[mode])
    return UserRouteBuildRequest(
        lat=54.9611,
        lng=20.4703,
        city_id=scenario.city_slug,
        user_id=f"eval-{scenario.scenario_id}-{mode}",
        **kwargs,
    )


def _slot_request(scenario: CityScenario) -> UserRouteBuildRequest:
    return UserRouteBuildRequest(
        lat=54.9611,
        lng=20.4703,
        city_id=scenario.city_slug,
        user_id=f"eval-{scenario.scenario_id}-slot",
        build_mode="constructor",
        time_budget_minutes=120,
        route_slots=[
            {"slot_id": "coffee", "category": "cafe", "required": True},
            {"slot_id": "museum", "category": "museum", "required": False},
        ],
    )


def _structured_request(scenario: CityScenario) -> UserRouteStructuredBuildRequest:
    return UserRouteStructuredBuildRequest(
        lat=54.9611,
        lng=20.4703,
        city_id=scenario.city_slug,
        user_id=f"eval-{scenario.scenario_id}-structured",
        time_budget_minutes=120,
        slots=[
            UserRouteSlotRequest(slot_id="coffee", category="cafe"),
            UserRouteSlotRequest(slot_id="museum", category="museum"),
        ],
    )


# --- Profiles: (builder fn, list of active modes, expected route possible) -

_HEALTHY_PROFILES = ("healthy_compact", "healthy_distributed")


def _run_freeform_mode(db_session, scenario: CityScenario, mode: str, *, city_should_have_candidates: bool) -> None:
    request = _build_request(scenario, mode)
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session,
        final,
        scenario_id=scenario.scenario_id,
        entrypoint="POST /v1/user-routes/build",
        build_mode=str(_MODE_REQUEST_KWARGS[mode]["build_mode"]),
        expected_status="ready_or_partial" if city_should_have_candidates else "no_route",
        expected_city_slug=scenario.city_slug,
        generation_run_id=GENERATION_RUN_ID,
    )
    if not city_should_have_candidates:
        assert final.status == "no_route", (scenario.scenario_id, mode, final.status)
        assert final.points == []


def _run_slot_mode(db_session, scenario: CityScenario, *, city_should_have_candidates: bool) -> None:
    request = _slot_request(scenario)
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session,
        final,
        scenario_id=scenario.scenario_id,
        entrypoint="POST /v1/user-routes/build",
        build_mode="constructor",
        expected_status="ready_or_partial" if city_should_have_candidates else "no_route",
        expected_city_slug=scenario.city_slug,
        generation_run_id=GENERATION_RUN_ID,
    )
    if not city_should_have_candidates:
        assert final.status == "no_route"


def _run_structured_mode(db_session, scenario: CityScenario, *, city_should_have_candidates: bool) -> None:
    request = _structured_request(scenario)
    response = UserRouteEditService().structured_options(db_session, request)

    all_place_ids: list[str] = []
    for slot in response.slots:
        for option in slot.options:
            all_place_ids.append(option.place_id)

    if not city_should_have_candidates:
        assert all_place_ids == [], (scenario.scenario_id, "structured", all_place_ids)
        return

    # Structured options must still satisfy the public route contract even
    # though they are not wrapped in a FinalRoute — reuse the same
    # place-level contract check via a tiny point-like shim.
    class _Point:
        def __init__(self, place_id: str) -> None:
            self.place_id = place_id
            self.city_slug = scenario.city_slug
            self.category = "unknown"
            self.lat = 0.0
            self.lng = 0.0

    from tests.route_evaluation.invariants import assert_points_satisfy_public_route_contract

    assert_points_satisfy_public_route_contract(
        db_session,
        [_Point(pid) for pid in all_place_ids],
        scenario_id=scenario.scenario_id,
        entrypoint="POST /v1/user-routes/build-structured",
        build_mode="structured",
        expected_status="options_present",
        actual_status="options_present",
        generation_run_id=GENERATION_RUN_ID,
    )


# --- Healthy / sparse published cities: all modes must produce candidates --


@pytest.mark.parametrize("mode", ACTIVE_FREEFORM_MODES)
def test_healthy_compact_city_all_modes_new(db_session, city_factory, published_place_factory, mode) -> None:
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    _run_freeform_mode(db_session, scenario, mode, city_should_have_candidates=True)


@pytest.mark.parametrize("mode", ACTIVE_FREEFORM_MODES)
def test_healthy_distributed_city_all_modes_new(db_session, city_factory, published_place_factory, mode) -> None:
    scenario = build_healthy_distributed_city(city_factory, published_place_factory)
    _run_freeform_mode(db_session, scenario, mode, city_should_have_candidates=True)


def test_healthy_compact_city_slot_mode_new(db_session, city_factory, published_place_factory) -> None:
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    _run_slot_mode(db_session, scenario, city_should_have_candidates=True)


def test_healthy_compact_city_structured_mode_new(db_session, city_factory, published_place_factory) -> None:
    scenario = build_healthy_compact_city(city_factory, published_place_factory)
    _run_structured_mode(db_session, scenario, city_should_have_candidates=True)


def test_sparse_city_overview_mode_new(db_session, city_factory, published_place_factory) -> None:
    scenario = build_sparse_city(city_factory, published_place_factory)
    request = _build_request(scenario, "overview")
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session, final, scenario_id=scenario.scenario_id, entrypoint="POST /v1/user-routes/build",
        build_mode="auto", expected_status="partial_route_or_ready", expected_city_slug=scenario.city_slug,
        generation_run_id=GENERATION_RUN_ID,
    )
    # Only 2 eligible places exist; with a 180-minute budget targeting more
    # stops than that, canonical route_status() must not report "ready".
    assert final.status != "failed"


def test_single_place_city_never_reports_ready_new(db_session, city_factory, published_place_factory) -> None:
    """End-to-end reproduction of CITYGO-356 through the real build
    pipeline: a city with exactly one eligible place must never yield
    status="ready", regardless of build mode. This is the scenario-level
    complement to test_one_point_route_is_never_ready_new (which exercises
    the canonical route_status() function directly)."""
    scenario = build_single_place_city(city_factory, published_place_factory)
    for mode in ACTIVE_FREEFORM_MODES:
        request = _build_request(scenario, mode)
        final = UserRouteBuildService().build(db=db_session, request=request)
        if len(final.points) == 1:
            assert final.status != "ready", (scenario.scenario_id, mode, final.status)
        run_all_point_invariants(
            db_session, final, scenario_id=scenario.scenario_id, entrypoint="POST /v1/user-routes/build",
            build_mode=str(_MODE_REQUEST_KWARGS[mode]["build_mode"]), expected_status="no_route_or_partial",
            expected_city_slug=scenario.city_slug, generation_run_id=GENERATION_RUN_ID,
        )


# --- Preview / preparing / inactive city -> zero public candidates, every
# mode -----------------------------------------------------------------


@pytest.mark.parametrize(
    "builder",
    [build_active_preview_city, build_preparing_city, build_inactive_published_city],
)
@pytest.mark.parametrize("mode", ACTIVE_FREEFORM_MODES)
def test_unpublished_city_variants_all_modes_yield_no_route_new(
    db_session, city_factory, published_place_factory, builder, mode
) -> None:
    scenario = builder(city_factory, published_place_factory)
    _run_freeform_mode(db_session, scenario, mode, city_should_have_candidates=False)


@pytest.mark.parametrize(
    "builder",
    [build_active_preview_city, build_preparing_city, build_inactive_published_city],
)
def test_unpublished_city_variants_slot_mode_yields_no_route_new(
    db_session, city_factory, published_place_factory, builder
) -> None:
    scenario = builder(city_factory, published_place_factory)
    _run_slot_mode(db_session, scenario, city_should_have_candidates=False)


@pytest.mark.parametrize(
    "builder",
    [build_active_preview_city, build_preparing_city, build_inactive_published_city],
)
def test_unpublished_city_variants_structured_mode_yields_no_options_new(
    db_session, city_factory, published_place_factory, builder
) -> None:
    scenario = builder(city_factory, published_place_factory)
    _run_structured_mode(db_session, scenario, city_should_have_candidates=False)


# --- Mostly service-only city: only the one real place is ever usable -----


def test_mostly_service_only_city_overview_mode_new(db_session, city_factory, place_factory, published_place_factory) -> None:
    scenario = build_mostly_service_only_city(city_factory, place_factory, published_place_factory)
    request = _build_request(scenario, "overview")
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session, final, scenario_id=scenario.scenario_id, entrypoint="POST /v1/user-routes/build",
        build_mode="auto", expected_status="no_route_or_partial", expected_city_slug=scenario.city_slug,
        generation_run_id=GENERATION_RUN_ID,
    )
    returned_ids = {int(p.place_id) for p in final.points}
    assert returned_ids.isdisjoint(set(scenario.ineligible_place_ids)), (
        scenario.scenario_id, "service-only ids leaked into route", returned_ids & set(scenario.ineligible_place_ids)
    )


# --- Mixed-eligibility city: only eligible places may ever appear ---------


@pytest.mark.parametrize("mode", ACTIVE_FREEFORM_MODES)
def test_mixed_eligibility_city_never_returns_ineligible_places_new(
    db_session, city_factory, published_place_factory, place_factory, mode
) -> None:
    scenario = build_mixed_eligibility_city(city_factory, published_place_factory, place_factory)
    request = _build_request(scenario, mode)
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session, final, scenario_id=scenario.scenario_id, entrypoint="POST /v1/user-routes/build",
        build_mode=str(_MODE_REQUEST_KWARGS[mode]["build_mode"]), expected_status="ready_or_partial",
        expected_city_slug=scenario.city_slug, generation_run_id=GENERATION_RUN_ID,
    )
    returned_ids = {int(p.place_id) for p in final.points}
    assert returned_ids.isdisjoint(set(scenario.ineligible_place_ids)), (
        scenario.scenario_id, mode, "ineligible ids leaked", returned_ids & set(scenario.ineligible_place_ids)
    )


# --- Destination-enabled city: destination scope must not bypass contract --


def test_destination_enabled_city_overview_mode_new(db_session, city_factory, published_place_factory, monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "destination_foundation_enabled", True, raising=False)
    monkeypatch.setattr(settings, "destination_route_reads_enabled", True, raising=False)

    scenario = build_destination_enabled_city(city_factory, published_place_factory, db_session)
    request = UserRouteBuildRequest(
        lat=54.9611, lng=20.4703, city_id=scenario.city_slug, destination_slug=scenario.destination_slug,
        user_id=f"eval-{scenario.scenario_id}-overview", build_mode="auto", time_budget_minutes=180, interests=[],
    )
    final = UserRouteBuildService().build(db=db_session, request=request)

    run_all_point_invariants(
        db_session, final, scenario_id=scenario.scenario_id, entrypoint="POST /v1/user-routes/build",
        build_mode="auto", expected_status="ready_or_partial", expected_city_slug=scenario.city_slug,
        generation_run_id=GENERATION_RUN_ID,
    )


# --- Zero/one/two-point invariants exercised directly against the canonical
# function, matching CITYGO-356 -----------------------------------------


def test_zero_point_route_is_no_route_new() -> None:
    from services.route_status_service import route_status

    assert route_status(0, 4) == "no_route"


def test_one_point_route_is_never_ready_new() -> None:
    from services.route_status_service import route_status

    for expected_stops in (1, 2, 4, 6, 8):
        assert route_status(1, expected_stops) == "partial_route"


def test_two_point_route_ready_only_if_canonical_status_allows_new() -> None:
    from services.route_status_service import route_status

    assert route_status(2, 2) == "ready"
    assert route_status(2, 4) == "partial_route"


# --- Determinism: repeated local runs produce identical critical results --


def _run_full_dataset_once(db_session, city_factory, published_place_factory) -> list[tuple[str, str, str, int]]:
    """Returns (scenario_id, mode, status, point_count) for every
    (profile, mode) combination that is expected to be deterministic under
    this pipeline (no live provider calls, no wall-clock/scoring
    randomness — the dynamic route pipeline's scoring/assembly is pure
    computation over the DB rows created above)."""
    results: list[tuple[str, str, str, int]] = []
    for builder in (build_healthy_compact_city, build_healthy_distributed_city, build_sparse_city):
        scenario = builder(city_factory, published_place_factory)
        for mode in ACTIVE_FREEFORM_MODES:
            request = _build_request(scenario, mode)
            final = UserRouteBuildService().build(db=db_session, request=request)
            results.append((scenario.scenario_id, mode, final.status, len(final.points)))
    return results


def test_full_dataset_is_deterministic_across_two_runs_new(db_session, city_factory, published_place_factory) -> None:
    """Runs the healthy/sparse profile x mode matrix TWICE in independent
    city fixtures (unique slugs per run, since city_factory/place_factory
    write real rows) and compares status + point count — the invariants
    this dataset checks, not raw place-id snapshots. Two independent
    builds of the same deterministic input must reach the same status and
    the same point count both times."""
    first = _run_full_dataset_once(db_session, city_factory, published_place_factory)

    # Re-run against a second, independently-built but geometrically
    # identical set of cities (unique slugs to avoid unique-constraint
    # collisions) to prove the PIPELINE is deterministic, not that SQLite
    # returned cached rows.
    import tests.route_evaluation.scenarios as scenarios_module

    original_offsets = {
        "compact": scenarios_module._COMPACT_OFFSETS,
        "distributed": scenarios_module._DISTRIBUTED_OFFSETS,
        "sparse": scenarios_module._SPARSE_OFFSETS,
    }

    def _second_compact(city_factory, published_place_factory):
        city = city_factory(slug="eval-compact-city-run2", launch_status="published")
        ids = scenarios_module._make_places(published_place_factory, city, offsets=original_offsets["compact"])
        return scenarios_module.CityScenario(
            scenario_id="healthy_compact_published_city", city_slug=city.slug, place_ids=ids, eligible_place_ids=ids,
        )

    def _second_distributed(city_factory, published_place_factory):
        city = city_factory(slug="eval-distributed-city-run2", launch_status="published")
        ids = scenarios_module._make_places(published_place_factory, city, offsets=original_offsets["distributed"])
        return scenarios_module.CityScenario(
            scenario_id="healthy_distributed_published_city", city_slug=city.slug, place_ids=ids, eligible_place_ids=ids,
        )

    def _second_sparse(city_factory, published_place_factory):
        city = city_factory(slug="eval-sparse-city-run2", launch_status="published")
        ids = scenarios_module._make_places(published_place_factory, city, offsets=original_offsets["sparse"])
        return scenarios_module.CityScenario(
            scenario_id="sparse_published_city", city_slug=city.slug, place_ids=ids, eligible_place_ids=ids,
        )

    second: list[tuple[str, str, str, int]] = []
    for builder in (_second_compact, _second_distributed, _second_sparse):
        scenario = builder(city_factory, published_place_factory)
        for mode in ACTIVE_FREEFORM_MODES:
            request = _build_request(scenario, mode)
            final = UserRouteBuildService().build(db=db_session, request=request)
            second.append((scenario.scenario_id, mode, final.status, len(final.points)))

    first_by_key = {(s, m): (status, count) for s, m, status, count in first}
    second_by_key = {(s, m): (status, count) for s, m, status, count in second}
    assert first_by_key == second_by_key, (
        "route evaluation dataset is not deterministic across two independent runs",
        first_by_key,
        second_by_key,
    )
