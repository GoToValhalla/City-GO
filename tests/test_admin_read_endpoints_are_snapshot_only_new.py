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


def test_coverage_gaps_page_never_refreshes_on_initial_load():
    source = (ROOT / "frontend" / "src" / "pages" / "admin" / "AdminCoverageGapsPage.tsx").read_text(encoding="utf-8")

    assert "useEffect(() => { load(false) }" in source
    assert "useEffect(() => { load(true) }" not in source
    assert "refresh=true" not in source
    assert "limit', '100'" in source


def test_route_readiness_get_uses_snapshot_reader_not_live_compute():
    source = (ROOT / "routers" / "admin_route_eligibility.py").read_text(encoding="utf-8")
    list_body = source.split('@router.get("/readiness"', 1)[1].split('@router.post("/readiness/{city_slug}/recalculate")', 1)[0]
    item_body = source.split('@router.get("/readiness/{city_slug}"', 1)[1]

    assert "list_cities_readiness" in list_body
    assert "city_readiness_snapshot" in item_body
    assert "compute_city_readiness" not in source
