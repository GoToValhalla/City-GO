from __future__ import annotations

from pathlib import Path

from scripts.production_smoke import DEFAULT_ADMIN_CHECKS, DEFAULT_BACKEND_CHECKS, ROUTE_SMOKE_PATH

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ci_workflow_stays_manual_only_new() -> None:
    workflow = _read(".github/workflows/ci.yml")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "schedule:" not in workflow


def test_ci_runs_route_public_contract_gate_before_full_backend_regression_new() -> None:
    workflow = _read(".github/workflows/ci.yml")

    gate_index = workflow.index("Route public contract gate")
    regression_index = workflow.index("Backend tests and coverage")
    assert gate_index < regression_index
    assert "python scripts/route_public_contract_gate.py" in workflow


def test_production_smoke_runs_after_successful_deploy_or_manual_dispatch_new() -> None:
    workflow = _read(".github/workflows/production-smoke.yml")

    assert "workflow_dispatch:" in workflow
    assert "workflow_run:" in workflow
    assert "01 · CITY GO · Production Deploy" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow


def test_production_smoke_route_check_is_enabled_by_default_new() -> None:
    workflow = _read(".github/workflows/production-smoke.yml")

    assert "CITY_GO_ROUTE_SMOKE_ENABLED: true" in workflow
    assert "CITY_GO_ROUTE_SMOKE_CITY_ID" in workflow
    assert "CITY_GO_ROUTE_SMOKE_LAT" in workflow
    assert "CITY_GO_ROUTE_SMOKE_LNG" in workflow


def test_production_smoke_expected_sha_comes_from_deploy_head_or_manual_input_new() -> None:
    workflow = _read(".github/workflows/production-smoke.yml")

    assert "EXPECTED_SHA: ${{ github.event.workflow_run.head_sha || inputs.expected_sha || '' }}" in workflow


def test_production_smoke_uses_frontend_api_proxy_for_backend_and_admin_checks_new() -> None:
    assert ROUTE_SMOKE_PATH.startswith("/api/v1/")
    assert all(path.startswith("/api/") for _, path in DEFAULT_BACKEND_CHECKS)
    assert all(path.startswith("/api/") for _, path in DEFAULT_ADMIN_CHECKS)


def test_production_smoke_uploads_safe_summary_and_json_artifacts_new() -> None:
    workflow = _read(".github/workflows/production-smoke.yml")

    assert "--summary-file /tmp/production-smoke/summary.txt" in workflow
    assert "--json-report /tmp/production-smoke/report.json" in workflow
    assert "name: production-smoke-report" in workflow
    assert "retention-days: 7" in workflow
