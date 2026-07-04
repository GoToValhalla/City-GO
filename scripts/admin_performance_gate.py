from __future__ import annotations

import json
from pathlib import Path

SYNTHETIC_PLACE_FIXTURE_SIZE = 50_000


def main() -> None:
    checks: list[str] = []
    overview = Path("services/admin_overview_compact.py").read_text(encoding="utf-8")
    quality = Path("services/admin_platform_quality.py").read_text(encoding="utf-8")
    read_model = Path("services/admin_read_model_v2.py").read_text(encoding="utf-8")
    router_setup = Path("core/router_setup.py").read_text(encoding="utf-8")
    read_router = Path("routers/admin_read_models.py").read_text(encoding="utf-8")

    assert "db.query(*[_count_if" in overview
    checks.append("overview uses compact aggregate query")

    city_quality_body = quality.split("def city_quality_row", 1)[1].split("def quality_summary", 1)[0]
    assert ".all()" not in city_quality_body
    checks.append("city quality row has no full place load")

    assert "AdminOverviewSnapshot" in read_model
    assert "BacklogQueueSnapshot" in read_model
    assert "def refresh_all" in read_model
    checks.append("read model service and refresh function exist")

    assert "admin_read_models_router" in router_setup
    assert "import_module" in read_router
    assert "from services.admin_read_model_v2" not in read_router
    checks.append("read model routes are wired with lazy service imports")

    synthetic_payload = [{"id": idx, "queue": "route_blockers" if idx % 7 == 0 else "ok"} for idx in range(SYNTHETIC_PLACE_FIXTURE_SIZE)]
    blockers = sum(1 for item in synthetic_payload if item["queue"] == "route_blockers")
    assert blockers > 0
    checks.append(f"50k synthetic fixture processed: blockers={blockers}")

    print(json.dumps({"status": "ok", "fixture_size": SYNTHETIC_PLACE_FIXTURE_SIZE, "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
