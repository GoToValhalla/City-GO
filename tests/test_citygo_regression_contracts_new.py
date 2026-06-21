from __future__ import annotations

from pathlib import Path

from services.route_pipeline_trace import compact_route_trace, route_debug_summary


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_deploy_runs_all_alembic_heads_and_fails_fast_new() -> None:
    compose = read("docker-compose.yml")
    deploy = read(".github/workflows/deploy.yml")

    assert "command: alembic upgrade heads" in compose
    assert "command: alembic upgrade head\n" not in compose
    assert "docker compose run --rm migrate" in deploy
    assert "docker compose up migrate" not in deploy
    assert "MIGRATE_EXIT=$?" in deploy
    assert "alembic heads" in deploy
    assert "alembic current" in deploy
    assert "Deploy aborted before runtime restart" in deploy


def test_deploy_retries_schema_guard_before_runtime_restart_new() -> None:
    deploy = read(".github/workflows/deploy.yml")

    schema_guard_pos = deploy.index("=== production schema guard ===")
    stop_backend_pos = deploy.index("=== stop backend-side services only")
    assert schema_guard_pos < stop_backend_pos
    assert "SCHEMA_GUARD_OK=0" in deploy
    assert "for attempt in 1 2 3" in deploy
    assert "production schema guard failed after retries" in deploy


def test_local_disk_cache_is_non_authoritative_and_persisted_new() -> None:
    cache_service = read("services/local_persistent_cache.py")
    compose = read("docker-compose.yml")
    settings = read("core/config.py")

    assert "not a source of truth" in cache_service
    assert "FanoutCache" in cache_service
    assert "local_cache:" in compose
    assert "- local_cache:/app/.cache/city-go" in compose
    assert "local_cache_enabled" in settings
    assert "local_cache_default_ttl_seconds" in settings


def test_external_enrichment_calls_use_read_through_cache_new() -> None:
    geocode = read("services/place_address_geocode.py")
    images = read("data/scripts/enrich_place_images.py")

    assert "CACHE_NAMESPACE = \"nominatim_reverse_v1\"" in geocode
    assert "get_cached_json(cache_key)" in geocode
    assert "set_cached_json(cache_key, payload, tag=\"provider:nominatim\")" in geocode
    assert "HTTP_TEXT_CACHE_NAMESPACE = \"image_enrichment_http_text_v1\"" in images
    assert "get_cached_text(cache_key)" in images
    assert "set_cached_text(cache_key, text" in images


def test_admin_import_actions_are_db_queued_not_fastapi_background_tasks_new() -> None:
    router = read("routers/admin_import_jobs.py")
    worker = read("services/admin_city_import_tasks.py")
    job_service = read("services/admin_city_import_job_service.py")
    compose = read("docker-compose.yml")

    assert "BackgroundTasks" not in router
    assert "background_tasks.add_task" not in router
    assert "queue_city_import_job" in router
    assert "queue_city_enrichment_job" in router
    assert '@router.get("/import-jobs/queue")' in router
    assert "import_queue_summary" in worker
    assert "SOURCE_FULL_IMPORT" in job_service
    assert "SOURCE_ENRICHMENT_ONLY" in job_service
    assert "IMPORT_WORKER_BATCH_LIMIT: 1" in compose
    assert "IMPORT_WORKER_SLEEP_SECONDS: 60" in compose


def test_route_debug_summary_detects_retrieval_death_new() -> None:
    trace = [
        {"stage": "candidate_retrieval", "count": 0, "places_total_in_city": 387, "places_route_visible": 215, "places_route_eligible": 159},
        {"stage": "hard_filter", "input_count": 0, "kept_count": 0},
    ]

    summary = route_debug_summary("route-1", trace)

    assert summary["death_point"] == "candidate_retrieval"
    assert summary["retrieval"]["final_candidates_count"] == 0
    assert summary["city"]["places_total_in_city"] == 387


def test_route_debug_summary_detects_assembly_death_new() -> None:
    trace = [
        {"stage": "candidate_retrieval", "count": 180},
        {"stage": "hard_filter", "input_count": 180, "kept_count": 115},
        {"stage": "scoring", "count": 115},
        {"stage": "assembly", "input_scored_count": 115, "selected_count": 1, "rejection_reasons": {"max_walk_minutes_for_stage_exceeded": 89}},
    ]

    summary = route_debug_summary("route-2", trace)

    assert summary["death_point"] == "assembly"
    assert summary["pipeline_counts"]["assembly_input"] == 115
    assert summary["pipeline_counts"]["assembly_output"] == 1
    assert summary["important"]["assembly_rejections"] == {"max_walk_minutes_for_stage_exceeded": 89}


def test_route_debug_summary_detects_budget_and_finalize_death_new() -> None:
    budget_trace = [
        {"stage": "candidate_retrieval", "count": 180},
        {"stage": "hard_filter", "input_count": 180, "kept_count": 115},
        {"stage": "scoring", "count": 115},
        {"stage": "assembly", "input_scored_count": 115, "selected_count": 2},
        {"stage": "budget_fit", "input_count": 2, "kept_count": 0},
    ]
    finalize_trace = [
        {"stage": "candidate_retrieval", "count": 180},
        {"stage": "hard_filter", "input_count": 180, "kept_count": 115},
        {"stage": "scoring", "count": 115},
        {"stage": "assembly", "input_scored_count": 115, "selected_count": 2},
        {"stage": "budget_fit", "input_count": 2, "kept_count": 2},
        {"stage": "final", "final_points_count": 0},
    ]

    assert route_debug_summary("route-3", budget_trace)["death_point"] == "budget_fit"
    assert route_debug_summary("route-4", finalize_trace)["death_point"] == "finalize"


def test_compact_route_trace_limits_heavy_samples_for_phone_debug_new() -> None:
    trace = [{
        "stage": "retrieval",
        "sample_candidates": [
            {"id": idx, "title": f"Place {idx}", "raw_payload": {"huge": list(range(100))}}
            for idx in range(20)
        ],
        "warnings": [f"warning-{idx}" for idx in range(40)],
        "unused_heavy_blob": {"x": list(range(1000))},
    }]

    compact = compact_route_trace(trace)

    assert len(compact[0]["sample_candidates"]) == 12
    assert "raw_payload" not in compact[0]["sample_candidates"][0]
    assert len(compact[0]["warnings"]) == 30
    assert "unused_heavy_blob" not in compact[0]


def test_frontend_route_debug_is_rendered_inline_without_nested_scroll_primitives_new() -> None:
    component = read("frontend/src/widgets/recommendation-route/RouteDebugTrace.tsx")

    assert "route-debug-summary-grid" in component
    assert "buildPipelineMatrix" in component
    assert "compactJson" in component
    assert "<pre" not in component
    assert "<textarea" not in component
    assert "<details" not in component
    assert "JSON.stringify(value)" in component
