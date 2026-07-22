from pathlib import Path

import yaml

from scripts.production_smoke import (
    DEFAULT_ROUTE_SMOKE_CITY_ID, DEFAULT_ROUTE_SMOKE_LAT, DEFAULT_ROUTE_SMOKE_LNG,
)

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/stage5-production-operations.yml"
SCRIPT = ROOT / "scripts/stage5_production_ops.py"


def test_stage5_workflow_is_manual_guarded_and_serialized_new() -> None:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    dispatch = data[True]["workflow_dispatch"]
    operations = dispatch["inputs"]["operation"]["options"]
    assert set(data[True]) == {"workflow_dispatch"}
    assert len(operations) == 10
    assert data["concurrency"] == {"group": "stage5-production-operations", "cancel-in-progress": False}
    assert data["jobs"]["operate"]["environment"] == "production"


def test_stage5_workflow_uses_only_canonical_api_helper_new() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    assert "python scripts/stage5_production_ops.py" in workflow
    assert "CONFIRM_STAGE5_PRODUCTION_MUTATION" in workflow
    assert "Authorization" in script
    assert "/api/admin/projections/rebuild" in script
    assert "/api/admin/projections/readiness" in script
    assert "/api/admin/feature-toggles/" in script
    assert "SELECT " not in workflow + script
    assert "DELETE " not in workflow + script


def test_stage5_helper_keeps_disable_independent_of_readiness_new() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    disable = script[script.index('if operation == "disable_all"'):]
    assert "readiness(True)" not in disable
    assert 'toggle(name, False)' in disable
    assert 'if enabled:' in script
    assert "activation-safety" in script


def test_production_smoke_uses_route_eligible_published_fixture_new() -> None:
    assert (DEFAULT_ROUTE_SMOKE_CITY_ID, DEFAULT_ROUTE_SMOKE_LAT, DEFAULT_ROUTE_SMOKE_LNG) == (
        "astrakhan", 46.3420642, 48.0209452,
    )
    workflow = (ROOT / ".github/workflows/production-smoke.yml").read_text(encoding="utf-8")
    assert "'astrakhan'" in workflow
    assert "'yerevan'" not in workflow
