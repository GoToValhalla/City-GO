from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_coverage_gaps_get_does_not_run_assurance_refresh():
    source = (ROOT / "routers" / "admin_coverage_gaps.py").read_text(encoding="utf-8")
    list_body = source.split('@router.get("")', 1)[1].split('@router.get("/cities/{city_slug}")', 1)[0]
    city_body = source.split('@router.get("/cities/{city_slug}")', 1)[1].split('@router.post("/sync")', 1)[0]

    assert "refresh: bool = False" in list_body
    assert "refresh: bool = False" in city_body
    assert "run_data_coverage_assurance(" not in list_body
    assert "run_data_coverage_assurance(" not in city_body
    assert "db.commit()" not in list_body
    assert "db.commit()" not in city_body


def test_coverage_gaps_page_uses_background_refresh_not_legacy_refresh():
    source = (ROOT / "frontend" / "src" / "pages" / "admin" / "AdminCoverageGapsSnapshotPage.tsx").read_text(encoding="utf-8")

    assert "useEffect(() => { void load() }" in source
    assert "refresh=true" not in source
    assert "/admin/background-operations/coverage-gaps/refresh" in source
    assert "/admin/background-operations/coverage-gaps/status" in source
    assert "/admin/coverage-gaps/refresh" not in source


def test_route_readiness_get_uses_snapshot_reader_not_live_compute():
    source = (ROOT / "routers" / "admin_route_eligibility.py").read_text(encoding="utf-8")
    list_body = source.split('@router.get("/readiness"', 1)[1].split('@router.post("/readiness/{city_slug}/recalculate")', 1)[0]
    item_body = source.split('@router.get("/readiness/{city_slug}"', 1)[1]

    assert "list_cities_readiness" in list_body
    assert "city_readiness_snapshot" in item_body
    assert "compute_city_readiness" not in source


def test_heavy_admin_posts_enqueue_durable_operations():
    background_router = (ROOT / "routers" / "admin_background_operations.py").read_text(encoding="utf-8")
    readiness_router = (ROOT / "routers" / "admin_route_eligibility.py").read_text(encoding="utf-8")
    address_router = (ROOT / "routers" / "admin_place_ops.py").read_text(encoding="utf-8")
    address_service = (ROOT / "services" / "admin_address_job_service.py").read_text(encoding="utf-8")
    queue_service = (ROOT / "services" / "admin_background_operation_service.py").read_text(encoding="utf-8")

    assert '@router.post("/coverage-gaps/refresh")' in background_router
    assert '@router.post("/city-readiness/recalculate")' in background_router
    assert "create_background_operation(" in background_router
    assert "create_background_operation(" in readiness_router
    assert "BackgroundTasks" not in background_router
    assert "BackgroundTasks" not in readiness_router
    assert "background_tasks.add_task(run_background_operation" not in background_router
    assert "background_tasks.add_task(run_background_operation" not in readiness_router
    assert "run_queued_background_operations" in queue_service
    assert "claim_next_background_operation" in queue_service
    assert "background_tasks.add_task(run_address_refresh_operation" in address_router
    assert 'status="queued"' in address_service
    assert "_run_refresh(" not in address_service.split("def queue_address_refresh", 1)[1].split("def run_address_refresh_operation", 1)[0]
