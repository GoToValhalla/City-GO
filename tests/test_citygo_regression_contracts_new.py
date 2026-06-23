from __future__ import annotations

from pathlib import Path

from services.route_pipeline_trace import compact_route_trace, route_debug_summary


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_deploy_repairs_known_alembic_overlap_and_fails_fast_new() -> None:
    compose = read("docker-compose.yml")
    deploy = read(".github/workflows/deploy.yml")

    assert 'if inspect(engine).has_table("alembic_version")' in compose
    assert '{"9d0e1f2a3b4c", "fb7e3c2a91d4"}.issubset(revisions)' in compose
    assert '"revision": "9d0e1f2a3b4c"' in compose
    assert "alembic upgrade head" in compose
    assert "alembic upgrade heads" not in compose
    assert "docker compose run" in deploy
    assert "migrate </dev/null" in deploy
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
