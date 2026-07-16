"""CITYGO-319/320: tiled OSM import integration and per-tile resume.

Covers: existing single-tile import behavior is byte-identical to before
(run() routes through tile mode only when plan_tiles() genuinely produces
more than one tile), independent per-tile apply, no duplicated places, no
gaps/overlaps between tiles, resume from the first unfinished tile after
a simulated crash, retry-on-transient-fetch-failure, and full diagnostics
(total/completed/failed/retried tiles, elapsed time, per-tile failure
reason).
"""

from __future__ import annotations

from unittest.mock import patch

import urllib.error

from data.scripts import import_city_osm
from models.city_import_scope import CityImportScope
from models.import_tile_run import ImportTileRun
from models.place import Place
from services.import_tile_run_service import (
    ensure_tile_runs,
    mark_tile_completed,
    mark_tile_failed,
    mark_tile_running,
    next_unfinished_tile_run,
    tile_progress_diagnostics,
)
from services.osm_tile_planner import TilePlannerConfig, plan_tiles


def _node(osm_id: int, *, name: str = "Кафе", amenity: str = "cafe", lat: float, lng: float) -> dict:
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lng, "tags": {"name": name, "amenity": amenity}}


def _small_scope(db_session, city_factory, *, slug: str = "small-city") -> tuple:
    city = city_factory(slug=slug)
    scope = CityImportScope(
        city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled",
        import_profile="tourist_core",
        bbox={"south": 54.92, "west": 20.44, "north": 54.98, "east": 20.53},
    )
    db_session.add(scope)
    db_session.commit()
    return city, scope


def _large_scope(db_session, city_factory, *, slug: str = "large-city") -> tuple:
    city = city_factory(slug=slug)
    scope = CityImportScope(
        city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled",
        import_profile="tourist_core",
        bbox={"south": 40.0, "west": 44.0, "north": 41.2, "east": 45.2},
    )
    db_session.add(scope)
    db_session.commit()
    return city, scope


# --- existing behavior unchanged for small imports ---


def test_small_bbox_plans_to_exactly_one_tile_new(db_session, city_factory):
    _, scope = _small_scope(db_session, city_factory)

    plan = plan_tiles(city_slug="small-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox)

    assert plan.tile_count == 1


def test_run_takes_single_shot_path_for_small_bbox_new(db_session, city_factory, monkeypatch):
    city, scope = _small_scope(db_session, city_factory)
    monkeypatch.setattr(import_city_osm, "SessionLocal", lambda: db_session)
    db_session.close = lambda: None  # keep the fixture-owned session alive across the `with` block

    raw = [_node(1, lat=54.95, lng=20.48)]
    apply_import_calls = []
    tiled_calls = []

    def fake_apply_import(db, city_arg, scope_arg, profile, raw_objects, normalized, job_id):
        apply_import_calls.append((raw_objects, normalized))
        return {"mode": "apply", "status": "success", "batch_id": 1, "created": 1}

    with patch.object(import_city_osm, "_fetch_osm_objects", return_value=raw), \
         patch.object(import_city_osm, "_apply_import", side_effect=fake_apply_import), \
         patch.object(import_city_osm, "_apply_import_tiled", side_effect=lambda *a, **k: tiled_calls.append(1)):
        result = import_city_osm.run(["--city", city.slug, "--scope", scope.code, "--profile", "tourist_core", "--apply"])

    assert len(apply_import_calls) == 1
    assert tiled_calls == []
    assert result["created"] == 1


# --- tile mode activates only when bbox exceeds tile limits ---


def test_large_bbox_plans_to_multiple_tiles_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64)

    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    assert plan.tile_count > 1


def test_run_routes_to_tiled_path_for_large_bbox_new(db_session, city_factory, monkeypatch):
    city, scope = _large_scope(db_session, city_factory)
    monkeypatch.setattr(import_city_osm, "SessionLocal", lambda: db_session)
    db_session.close = lambda: None
    monkeypatch.setattr(
        import_city_osm, "TILE_PLANNER_CONFIG",
        TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64),
    )

    single_shot_calls = []
    tiled_calls = []
    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=lambda *a: single_shot_calls.append(1) or []), \
         patch.object(import_city_osm, "_apply_import_tiled", side_effect=lambda *a, **k: tiled_calls.append(1) or {"status": "success", "tiled": True}):
        import_city_osm.run(["--city", city.slug, "--scope", scope.code, "--profile", "tourist_core", "--apply"])

    assert tiled_calls == [1]
    assert single_shot_calls == []  # the single-shot _fetch_osm_objects call is never made in tile mode


# --- each tile imported independently, no duplicated places, no gaps/overlaps ---


def test_tiled_apply_creates_independent_batches_per_tile_new(db_session, city_factory):
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    assert plan.tile_count >= 2

    places_per_tile = {
        plan.tiles[0].tile_id: [_node(1, name="Кафе Раз", lat=plan.tiles[0].south + 0.01, lng=plan.tiles[0].west + 0.01)],
        plan.tiles[1].tile_id: [_node(2, name="Кафе Два", lat=plan.tiles[1].south + 0.01, lng=plan.tiles[1].west + 0.01)],
    }

    def fake_fetch(bbox, profile):
        for tile in plan.tiles:
            if abs(tile.south - bbox["south"]) < 1e-6 and abs(tile.west - bbox["west"]) < 1e-6:
                return places_per_tile.get(tile.tile_id, [])
        return []

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=fake_fetch):
        result = import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    assert result["tiled"] is True
    assert result["tile_diagnostics"]["total_tiles"] == plan.tile_count
    assert result["tile_diagnostics"]["completed"] == plan.tile_count

    places = db_session.query(Place).filter(Place.city_id == city.id).all()
    titles = {p.title for p in places}
    assert "Кафе Раз" in titles
    assert "Кафе Два" in titles
    assert len(places) == len(set(p.slug for p in places))  # no duplicated places


def test_tiles_do_not_overlap_or_gap_for_large_scope_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    by_row: dict[float, list] = {}
    for tile in plan.tiles:
        by_row.setdefault(tile.south, []).append(tile)
    for row_tiles in by_row.values():
        row_tiles.sort(key=lambda t: t.west)
        for left, right in zip(row_tiles, row_tiles[1:]):
            assert left.east == right.west


# --- retry applied only to OSM fetch, not to _apply_import ---


def test_transient_fetch_failure_is_retried_new(db_session, city_factory):
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    call_counts: dict[str, int] = {}

    def flaky_fetch(bbox, profile):
        key = f"{bbox['south']}:{bbox['west']}"
        call_counts[key] = call_counts.get(key, 0) + 1
        if key == f"{plan.tiles[0].south}:{plan.tiles[0].west}" and call_counts[key] < 2:
            raise urllib.error.HTTPError(url="x", code=503, msg="err", hdrs=None, fp=None)
        return []

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=flaky_fetch), \
         patch("services.osm_fetch_retry.DEFAULT_OSM_RETRY_CONFIG") as _unused:
        pass  # ensure module import path is exercised; real call below uses the real default config with real (tiny) sleeps

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=flaky_fetch):
        result = import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    assert result["tile_diagnostics"]["retried_tiles"] >= 1
    assert result["tile_diagnostics"]["total_retry_attempts"] >= 1
    assert result["tile_diagnostics"]["completed"] == plan.tile_count


def test_non_retryable_fetch_error_fails_tile_without_retry_loop_new(db_session, city_factory):
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    def always_bad_request(bbox, profile):
        raise urllib.error.HTTPError(url="x", code=400, msg="bad request", hdrs=None, fp=None)

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=always_bad_request):
        result = import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    assert result["tile_diagnostics"]["failed"] == plan.tile_count
    assert result["tile_diagnostics"]["retried_tiles"] == 0
    assert result["status"] == "partial_success"
    for tile_diag in result["tile_diagnostics"]["tiles"]:
        assert tile_diag["status"] == "failed"
        assert tile_diag["retry_attempts"] == 0


# --- tile failures never lose already-completed tiles; resume continues from the next unfinished tile ---


def test_tile_failure_does_not_lose_already_completed_tiles_new(db_session, city_factory):
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    assert plan.tile_count >= 2

    def fetch_first_ok_second_fails(bbox, profile):
        if abs(bbox["south"] - plan.tiles[0].south) < 1e-6 and abs(bbox["west"] - plan.tiles[0].west) < 1e-6:
            return [_node(1, lat=plan.tiles[0].south + 0.01, lng=plan.tiles[0].west + 0.01)]
        raise urllib.error.HTTPError(url="x", code=400, msg="bad", hdrs=None, fp=None)

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=fetch_first_ok_second_fails):
        result = import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    assert result["tile_diagnostics"]["completed"] == 1
    assert result["tile_diagnostics"]["failed"] >= 1
    places = db_session.query(Place).filter(Place.city_id == city.id).all()
    assert len(places) == 1  # tile 1's real place survives despite tile 2 failing


def test_resume_continues_from_next_unfinished_tile_new(db_session, city_factory):
    """Resume of the SAME execution: the manually-seeded rows and the
    orchestrator call below share execution_id="job:555" because both are
    keyed off the same city_admin_import_job_id (CITYGO-338)."""
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    assert plan.tile_count >= 2

    # Simulate a prior interrupted run of the same execution: tile 1
    # already completed, rest queued.
    rows = ensure_tile_runs(db_session, execution_id="job:555", scope_id=scope.id, city_admin_import_job_id=555, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    mark_tile_running(db_session, rows[0])
    mark_tile_completed(db_session, rows[0], batch_id=None, counters={"created": 1}, retry_attempts=0)
    db_session.commit()

    fetch_calls = []

    def fetch_and_record(bbox, profile):
        fetch_calls.append((bbox["south"], bbox["west"]))
        return []

    with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=fetch_and_record):
        import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, 555)

    # tile 1 (already completed before this call) must never be re-fetched
    assert (plan.tiles[0].south, plan.tiles[0].west) not in fetch_calls
    # every remaining tile IS fetched
    remaining = [(t.south, t.west) for t in plan.tiles[1:]]
    assert set(fetch_calls) == set(remaining)


def test_repeated_launch_with_same_job_id_is_idempotent_and_safe_new(db_session, city_factory):
    """CITYGO-338: calling _apply_import_tiled twice in a row for the SAME
    execution (same city_admin_import_job_id, e.g. a worker retrying the
    same job) must not re-run already-completed tiles or duplicate
    ImportTileRun rows — the two calls share one execution_id."""
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    with patch.object(import_city_osm, "_fetch_osm_objects", return_value=[]):
        import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, 777)
        fetch_calls_second_run = []
        with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=lambda *a: fetch_calls_second_run.append(1) or []):
            import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, 777)

    assert fetch_calls_second_run == []  # every tile was already terminal, nothing re-fetched
    rows = db_session.query(ImportTileRun).filter(ImportTileRun.scope_id == scope.id).all()
    assert len(rows) == plan.tile_count  # no duplicate rows created by the second call
    assert all(row.execution_id == "job:777" for row in rows)


def test_new_execution_without_job_id_reprocesses_every_tile_new(db_session, city_factory):
    """CITYGO-338: a NEW execution (no job id -> a fresh execution_id is
    minted each call) must create fresh rows and process every tile, even
    though an earlier execution of the same scope already completed all
    of its tiles. Nothing from the earlier execution is deleted."""
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    with patch.object(import_city_osm, "_fetch_osm_objects", return_value=[]):
        import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)
        fetch_calls_second_run = []
        with patch.object(import_city_osm, "_fetch_osm_objects", side_effect=lambda *a: fetch_calls_second_run.append(1) or []):
            import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    assert len(fetch_calls_second_run) == plan.tile_count  # every tile refetched by the new execution
    rows = db_session.query(ImportTileRun).filter(ImportTileRun.scope_id == scope.id).all()
    assert len(rows) == plan.tile_count * 2  # first execution's rows preserved as history, second execution's rows added
    execution_ids = {row.execution_id for row in rows}
    assert len(execution_ids) == 2  # two distinct executions, never sharing a checkpoint


def test_concurrent_executions_do_not_share_checkpoints_new(db_session, city_factory):
    """CITYGO-338: two 'concurrent' executions (two different job ids for
    the same scope) never see each other's tile rows."""
    from services.import_tile_run_service import ensure_tile_runs

    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    rows_a = ensure_tile_runs(db_session, execution_id="job:101", scope_id=scope.id, city_admin_import_job_id=101, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    mark_tile_running(db_session, rows_a[0])
    mark_tile_completed(db_session, rows_a[0], batch_id=None, counters=None, retry_attempts=0)
    db_session.commit()

    rows_b = ensure_tile_runs(db_session, execution_id="job:202", scope_id=scope.id, city_admin_import_job_id=202, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    assert all(row.status == "queued" for row in rows_b)  # execution B never sees execution A's completed tile
    assert next_unfinished_tile_run(rows_b) is not None
    assert next_unfinished_tile_run(rows_b).tile_id == rows_b[0].tile_id


def test_diagnostics_are_scoped_to_one_execution_new(db_session, city_factory):
    """CITYGO-338: tile_progress_diagnostics for one execution's rows must
    not be inflated by a different execution's rows for the same scope."""
    from services.import_tile_run_service import ensure_tile_runs

    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    rows_a = ensure_tile_runs(db_session, execution_id="job:301", scope_id=scope.id, city_admin_import_job_id=301, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    for row in rows_a:
        mark_tile_running(db_session, row)
        mark_tile_completed(db_session, row, batch_id=None, counters=None, retry_attempts=0)
    db_session.commit()

    rows_b = ensure_tile_runs(db_session, execution_id="job:302", scope_id=scope.id, city_admin_import_job_id=302, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    diag_b = tile_progress_diagnostics(rows_b)
    assert diag_b["total_tiles"] == plan.tile_count  # only execution B's rows, not A's + B's combined
    assert diag_b["completed"] == 0
    assert diag_b["queued"] == plan.tile_count


def test_failed_tile_gets_explicit_retry_within_retry_budget_new(db_session, city_factory):
    """CITYGO-338: a failed tile within the current execution is
    automatically requeued (retry_failed_tile_runs) up to
    MAX_TILE_RETRY_ATTEMPTS, then stays terminal."""
    from services.import_tile_run_service import MAX_TILE_RETRY_ATTEMPTS, ensure_tile_runs, retry_failed_tile_runs

    city, scope = _small_scope(db_session, city_factory)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox)
    rows = ensure_tile_runs(db_session, execution_id="job:401", scope_id=scope.id, city_admin_import_job_id=401, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    mark_tile_running(db_session, rows[0])
    mark_tile_failed(db_session, rows[0], failure_reason="boom", retry_attempts=MAX_TILE_RETRY_ATTEMPTS - 1)
    db_session.commit()

    requeued = retry_failed_tile_runs(db_session, rows)
    assert requeued == 1
    assert rows[0].status == "queued"

    mark_tile_running(db_session, rows[0])
    mark_tile_failed(db_session, rows[0], failure_reason="boom again", retry_attempts=MAX_TILE_RETRY_ATTEMPTS)
    db_session.commit()

    requeued_again = retry_failed_tile_runs(db_session, rows)
    assert requeued_again == 0  # retry budget exhausted, stays failed (terminal)
    assert rows[0].status == "failed"


# --- full diagnostics ---


def test_tile_diagnostics_report_truthful_counts_new(db_session, city_factory):
    city, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug=city.slug, scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    with patch.object(import_city_osm, "_fetch_osm_objects", return_value=[]):
        result = import_city_osm._apply_import_tiled(db_session, city, scope, "tourist_core", plan, None)

    diag = result["tile_diagnostics"]
    assert diag["total_tiles"] == plan.tile_count
    assert diag["completed"] == plan.tile_count
    assert diag["failed"] == 0
    assert diag["elapsed_seconds"] >= 0
    assert len(diag["tiles"]) == plan.tile_count


# --- CITYGO-320: persistence/resume service unit tests ---


def test_ensure_tile_runs_creates_one_row_per_tile_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)

    assert len(rows) == plan.tile_count
    assert all(row.status == "queued" for row in rows)
    assert [row.sequence for row in rows] == sorted(row.sequence for row in rows)


def test_ensure_tile_runs_is_idempotent_no_duplicate_rows_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)

    ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    rows = db_session.query(ImportTileRun).filter(ImportTileRun.scope_id == scope.id).all()
    assert len(rows) == plan.tile_count


def test_next_unfinished_tile_run_skips_terminal_rows_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.5, max_tile_height_deg=0.5, max_tile_count=16)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    mark_tile_running(db_session, rows[0])
    mark_tile_completed(db_session, rows[0], batch_id=None, counters=None, retry_attempts=0)
    db_session.commit()

    next_row = next_unfinished_tile_run(rows)

    assert next_row.tile_id == rows[1].tile_id


def test_next_unfinished_tile_run_returns_none_when_all_terminal_new(db_session, city_factory):
    _, scope = _small_scope(db_session, city_factory)
    plan = plan_tiles(city_slug="small-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    mark_tile_running(db_session, rows[0])
    mark_tile_completed(db_session, rows[0], batch_id=None, counters=None, retry_attempts=0)
    db_session.commit()

    assert next_unfinished_tile_run(rows) is None


def test_mark_tile_failed_preserves_failure_reason_and_retry_attempts_new(db_session, city_factory):
    _, scope = _small_scope(db_session, city_factory)
    plan = plan_tiles(city_slug="small-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    mark_tile_running(db_session, rows[0])
    mark_tile_failed(db_session, rows[0], failure_reason="HTTP 503 exhausted retries", retry_attempts=3)
    db_session.commit()

    row = db_session.query(ImportTileRun).filter(ImportTileRun.id == rows[0].id).one()
    assert row.status == "failed"
    assert row.failure_reason == "HTTP 503 exhausted retries"
    assert row.retry_attempts == 3


def test_tile_progress_diagnostics_reports_queued_running_completed_failed_skipped_new(db_session, city_factory):
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    mark_tile_running(db_session, rows[0])
    mark_tile_completed(db_session, rows[0], batch_id=None, counters=None, retry_attempts=0)
    mark_tile_running(db_session, rows[1])
    mark_tile_failed(db_session, rows[1], failure_reason="boom", retry_attempts=1)
    db_session.commit()

    diag = tile_progress_diagnostics(rows)

    assert diag["total_tiles"] == plan.tile_count
    assert diag["completed"] == 1
    assert diag["failed"] == 1
    assert diag["queued"] == plan.tile_count - 2
    assert diag["running"] == 0
    assert diag["skipped"] == 0
    assert diag["remaining"] == plan.tile_count - 2
    assert 0 <= diag["total_progress_pct"] <= 100


def test_tile_progress_diagnostics_eta_none_when_nothing_finished_new(db_session, city_factory):
    """ETA must never be fabricated from zero completed tiles."""
    _, scope = _large_scope(db_session, city_factory)
    config = TilePlannerConfig(max_tile_width_deg=0.3, max_tile_height_deg=0.3, max_tile_count=64)
    plan = plan_tiles(city_slug="large-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox, config=config)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()

    from datetime import datetime, timedelta
    diag = tile_progress_diagnostics(rows, started_at=datetime.utcnow() - timedelta(seconds=5))

    assert diag["eta_seconds"] is None
    assert diag["elapsed_seconds"] is not None


def test_tile_progress_diagnostics_progress_pct_100_when_all_complete_new(db_session, city_factory):
    _, scope = _small_scope(db_session, city_factory)
    plan = plan_tiles(city_slug="small-city", scope_code=scope.code, profile="tourist_core", bbox=scope.bbox)
    rows = ensure_tile_runs(db_session, execution_id="test-exec", scope_id=scope.id, city_admin_import_job_id=None, planner_version=plan.planner_version, tiles=plan.tiles)
    db_session.commit()
    mark_tile_running(db_session, rows[0])
    mark_tile_completed(db_session, rows[0], batch_id=None, counters=None, retry_attempts=0)
    db_session.commit()

    diag = tile_progress_diagnostics(rows)

    assert diag["total_progress_pct"] == 100.0
    assert diag["remaining"] == 0
