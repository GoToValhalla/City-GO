"""CITYGO-317: deterministic spatial tile planner for OSM ingestion.

All tests exercise services/osm_tile_planner.py directly and in isolation
— this module is dark-launched and has zero callers in the current import
path (see test_osm_tile_planner_has_no_current_import_callers_new below,
which proves that at the source-code level, not just by omission).
"""

from __future__ import annotations

import re

from services.osm_tile_planner import (
    PLANNER_VERSION,
    Tile,
    TilePlan,
    TilePlannerConfig,
    TilePlannerError,
    plan_tiles,
    plan_tiles_diagnostics,
)


ZELENOGRADSK_BBOX = {"south": 54.90, "west": 20.40, "north": 54.95, "east": 20.50}
YEREVAN_LARGE_BBOX = {"south": 40.0, "west": 44.0, "north": 41.5, "east": 45.2}


def _small_config() -> TilePlannerConfig:
    return TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64)


# --- deterministic repeat ---


def test_deterministic_repeat_same_input_same_output_new():
    plan1 = plan_tiles(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX, config=_small_config())
    plan2 = plan_tiles(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX, config=_small_config())

    assert plan1.tile_count == plan2.tile_count
    assert [t.tile_id for t in plan1.tiles] == [t.tile_id for t in plan2.tiles]
    assert [(t.south, t.west, t.north, t.east) for t in plan1.tiles] == [(t.south, t.west, t.north, t.east) for t in plan2.tiles]
    assert [t.sequence for t in plan1.tiles] == [t.sequence for t in plan2.tiles]


def test_deterministic_across_many_repeated_calls_new():
    plans = [
        plan_tiles(city_slug="almaty", scope_code="tourist_core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())
        for _ in range(10)
    ]
    reference_ids = [t.tile_id for t in plans[0].tiles]
    for plan in plans[1:]:
        assert [t.tile_id for t in plan.tiles] == reference_ids


def test_tile_ids_do_not_use_random_uuids_new():
    plan = plan_tiles(city_slug="kutaisi", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX)
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    for tile in plan.tiles:
        assert not uuid_pattern.match(tile.tile_id)
        assert tile.tile_id.startswith("tile_")


# --- one-tile city ---


def test_small_city_produces_exactly_one_tile_new():
    plan = plan_tiles(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX)

    assert plan.tile_count == 1
    tile = plan.tiles[0]
    assert tile.sequence == 1
    assert tile.total_tiles == 1
    assert tile.south == ZELENOGRADSK_BBOX["south"]
    assert tile.west == ZELENOGRADSK_BBOX["west"]
    assert tile.north == ZELENOGRADSK_BBOX["north"]
    assert tile.east == ZELENOGRADSK_BBOX["east"]


def test_one_tile_carries_full_identity_new():
    plan = plan_tiles(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX)
    tile = plan.tiles[0]

    assert isinstance(tile, Tile)
    assert tile.city_slug == "zelenogradsk"
    assert tile.scope_code == "core"
    assert tile.profile == "tourist_core"
    assert tile.tile_id


# --- multi-tile city ---


def test_large_city_produces_multiple_tiles_new():
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    assert plan.tile_count > 1
    assert plan.rows > 1 or plan.cols > 1
    assert all(t.total_tiles == plan.tile_count for t in plan.tiles)


def test_non_square_bbox_produces_asymmetric_grid_new():
    """~1.5 deg latitude span vs ~1.2 deg longitude span at 0.3 deg tiles ->
    different row/col counts."""
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    assert plan.rows != plan.cols


# --- exact shared boundaries without gaps ---


def test_adjacent_tiles_share_exact_boundaries_no_gaps_new():
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    by_row: dict[float, list[Tile]] = {}
    for tile in plan.tiles:
        by_row.setdefault(tile.south, []).append(tile)

    for row_tiles in by_row.values():
        row_tiles.sort(key=lambda t: t.west)
        for left, right in zip(row_tiles, row_tiles[1:]):
            assert left.east == right.west, f"gap/overlap between {left} and {right}"

    by_col: dict[float, list[Tile]] = {}
    for tile in plan.tiles:
        by_col.setdefault(tile.west, []).append(tile)
    for col_tiles in by_col.values():
        col_tiles.sort(key=lambda t: t.south)
        for bottom, top in zip(col_tiles, col_tiles[1:]):
            assert bottom.north == top.south, f"gap/overlap between {bottom} and {top}"


def test_grid_exactly_covers_original_bbox_new():
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    assert min(t.south for t in plan.tiles) == YEREVAN_LARGE_BBOX["south"]
    assert min(t.west for t in plan.tiles) == YEREVAN_LARGE_BBOX["west"]
    assert max(t.north for t in plan.tiles) == YEREVAN_LARGE_BBOX["north"]
    assert max(t.east for t in plan.tiles) == YEREVAN_LARGE_BBOX["east"]


def test_total_tile_area_matches_original_bbox_area_new():
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    total_area = sum((t.east - t.west) * (t.north - t.south) for t in plan.tiles)
    original_area = (YEREVAN_LARGE_BBOX["east"] - YEREVAN_LARGE_BBOX["west"]) * (YEREVAN_LARGE_BBOX["north"] - YEREVAN_LARGE_BBOX["south"])
    assert abs(total_area - original_area) < 1e-6


# --- stable ordering ---


def test_tile_sequence_is_contiguous_south_to_north_west_to_east_new():
    plan = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    assert [t.sequence for t in plan.tiles] == list(range(1, plan.tile_count + 1))

    first_row = [t for t in plan.tiles if t.sequence <= plan.cols]
    assert [t.west for t in first_row] == sorted(t.west for t in first_row)

    row_souths = [plan.tiles[row_index * plan.cols].south for row_index in range(plan.rows)]
    assert row_souths == sorted(row_souths)


def test_ordering_stable_across_repeated_calls_new():
    plan1 = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())
    plan2 = plan_tiles(city_slug="yerevan", scope_code="core", profile="tourist_core", bbox=YEREVAN_LARGE_BBOX, config=_small_config())

    assert [(t.sequence, t.tile_id) for t in plan1.tiles] == [(t.sequence, t.tile_id) for t in plan2.tiles]


# --- negative coordinates ---


def test_negative_coordinates_produce_valid_plan_new():
    bbox = {"south": -34.61, "west": -58.45, "north": -34.55, "east": -58.35}
    plan = plan_tiles(city_slug="buenosaires", scope_code="core", profile="tourist_core", bbox=bbox)

    assert plan.tile_count >= 1
    assert plan.tiles[0].south == bbox["south"]
    assert plan.tiles[-1].north == bbox["north"]


def test_negative_coordinates_deterministic_new():
    bbox = {"south": -34.61, "west": -58.45, "north": -34.55, "east": -58.35}
    plan1 = plan_tiles(city_slug="buenosaires", scope_code="core", profile="tourist_core", bbox=bbox)
    plan2 = plan_tiles(city_slug="buenosaires", scope_code="core", profile="tourist_core", bbox=bbox)

    assert [t.tile_id for t in plan1.tiles] == [t.tile_id for t in plan2.tiles]


# --- invalid bbox ---


def test_invalid_bbox_south_greater_than_north_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": 10, "west": 10, "north": 5, "east": 20})
        assert False, "expected TilePlannerError"
    except TilePlannerError as exc:
        assert "south" in str(exc) and "north" in str(exc)


def test_invalid_bbox_missing_key_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": 10, "west": 10, "north": 20})
        assert False, "expected TilePlannerError"
    except TilePlannerError as exc:
        assert "east" in str(exc)


def test_invalid_bbox_non_numeric_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": "north-ish", "west": 10, "north": 20, "east": 20})
        assert False, "expected TilePlannerError"
    except TilePlannerError:
        pass


def test_invalid_bbox_out_of_range_latitude_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": -95, "west": 10, "north": 20, "east": 20})
        assert False, "expected TilePlannerError"
    except TilePlannerError as exc:
        assert "latitude" in str(exc)


def test_empty_city_slug_fails_closed_new():
    try:
        plan_tiles(city_slug="", scope_code="c", profile="p", bbox=ZELENOGRADSK_BBOX)
        assert False, "expected TilePlannerError"
    except TilePlannerError:
        pass


def test_invalid_config_fails_closed_new():
    try:
        TilePlannerConfig(max_tile_width_deg=0)
        assert False, "expected TilePlannerError"
    except TilePlannerError:
        pass
    try:
        TilePlannerConfig(max_tile_count=0)
        assert False, "expected TilePlannerError"
    except TilePlannerError:
        pass


# --- excessive tile count ---


def test_excessive_tile_count_fails_closed_new():
    tiny_tile_config = TilePlannerConfig(max_tile_width_deg=0.01, max_tile_height_deg=0.01, max_tile_count=100)
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": 0, "west": 0, "north": 10, "east": 10}, config=tiny_tile_config)
        assert False, "expected TilePlannerError"
    except TilePlannerError as exc:
        assert "max_tile_count" in str(exc)


def test_tile_count_within_limit_succeeds_new():
    config = TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=100)
    plan = plan_tiles(city_slug="x", scope_code="c", profile="p", bbox=YEREVAN_LARGE_BBOX, config=config)
    assert plan.tile_count <= 100


# --- antimeridian ---


def test_antimeridian_crossing_bbox_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": -10, "west": 170, "north": 10, "east": -170})
        assert False, "expected TilePlannerError"
    except TilePlannerError as exc:
        assert "antimeridian" in str(exc)


def test_west_equal_east_fails_closed_new():
    try:
        plan_tiles(city_slug="x", scope_code="c", profile="p", bbox={"south": -10, "west": 10, "north": 10, "east": 10})
        assert False, "expected TilePlannerError"
    except TilePlannerError:
        pass


# --- diagnostics ---


def test_diagnostics_reports_truthful_success_new():
    plan = plan_tiles(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX)
    diag = plan.diagnostics()

    assert diag["planner_version"] == PLANNER_VERSION
    assert diag["tile_count"] == 1
    assert diag["original_bbox"] == {"south": 54.9, "west": 20.4, "north": 54.95, "east": 20.5}
    assert diag["rejection_reason"] is None


def test_diagnostics_wrapper_reports_rejection_reason_without_raising_new():
    diag = plan_tiles_diagnostics(city_slug="x", scope_code="c", profile="p", bbox={"south": 10, "west": 10, "north": 5, "east": 20})

    assert diag["tile_count"] == 0
    assert diag["rejection_reason"] is not None
    assert "south" in diag["rejection_reason"]


def test_diagnostics_wrapper_reports_success_same_as_plan_new():
    diag = plan_tiles_diagnostics(city_slug="zelenogradsk", scope_code="core", profile="tourist_core", bbox=ZELENOGRADSK_BBOX)

    assert diag["tile_count"] == 1
    assert diag["rejection_reason"] is None


# --- no integration with current importer (dark launch) ---


def test_osm_tile_planner_has_no_current_import_callers_new():
    """Requirement 8: no import job may start using tiles automatically
    without deliberate wiring. CITYGO-319 explicitly wires plan_tiles
    into data/scripts/import_city_osm.py's tile-mode-activation branch,
    so that file is excluded here. Every other entrypoint must still not
    reference the tile planner."""
    from pathlib import Path

    entrypoints = (
        Path("data/scripts/import_city_osm_v2.py"),
        Path("data/scripts/run_due_import_jobs.py"),
        Path("services/admin_city_import_runner.py"),
        Path("services/admin_city_import_job_service.py"),
        Path("services/admin_city_import_tasks.py"),
        Path("services/import_pipeline/runner.py"),
    )
    for path in entrypoints:
        assert path.exists(), f"expected entrypoint file missing: {path}"
        source = path.read_text(encoding="utf-8")
        assert "osm_tile_planner" not in source, f"{path} must not reference osm_tile_planner yet"
        assert "plan_tiles" not in source, f"{path} must not call plan_tiles yet"


def test_plan_tiles_is_a_pure_function_no_db_no_side_effects_new():
    """The planner module must not import db/session, sqlalchemy models,
    or anything else that would let it silently touch persisted state."""
    import inspect

    import services.osm_tile_planner as module

    source = inspect.getsource(module)
    for forbidden in ("db.session", "SessionLocal", "import requests", "urllib.request", "sqlalchemy"):
        assert forbidden not in source, f"planner module must stay pure/dark-launched, found forbidden reference: {forbidden}"
