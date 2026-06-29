from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_admin_get_routes_do_not_default_to_refresh_true():
    offenders = []
    for path in (ROOT / "routers").glob("admin*.py"):
        text = path.read_text(encoding="utf-8")
        if "@router.get" in text and ("refresh: bool = True" in text or "refresh=True" in text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_admin_coverage_gaps_get_is_snapshot_only():
    text = (ROOT / "routers" / "admin_coverage_gaps.py").read_text(encoding="utf-8")
    get_block = text.split('@router.get("/cities/{city_slug}")')[0]
    list_block = get_block.split('@router.get("")', 1)[1]
    assert "run_data_coverage_assurance" not in list_block
    assert "apply_coverage_readiness_gate" not in list_block
    assert "build_coverage_summary" in list_block


def test_frontend_admin_pages_do_not_autoload_refresh_true():
    offenders = []
    for path in (ROOT / "frontend" / "src" / "pages" / "admin").glob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        if "refresh=true" in text or "refresh', 'true'" in text or 'refresh", "true"' in text:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []
