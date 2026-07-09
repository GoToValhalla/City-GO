"""Deploy workflow guardrails for the production import worker."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def _compose_services() -> Mapping[str, Mapping[str, object]]:
    data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    services = data["services"]
    assert isinstance(services, dict)
    return services


def _workflow() -> str:
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def test_import_worker_is_the_profiled_worker_service_new() -> None:
    services = _compose_services()
    worker = services["import-worker"]

    assert worker.get("profiles") == ["ops"]
    assert worker.get("command") == "python data/scripts/run_admin_import_worker.py"


def test_ops_profile_services_are_known_and_not_all_deploy_safe_new() -> None:
    services = _compose_services()
    ops_services = sorted(
        name
        for name, service in services.items()
        if "ops" in service.get("profiles", [])
    )

    assert ops_services == [
        "address-backfill",
        "import-worker",
        "place-enrichment-export",
        "seed",
    ]


def test_deploy_restarts_import_worker_after_removing_it_new() -> None:
    text = _workflow()
    stop_idx = text.index("docker compose stop frontend backend import-worker bot")
    rm_idx = text.index("docker compose rm -f frontend backend import-worker bot")
    start_idx = text.index("timeout 120s docker compose up -d --no-deps import-worker")
    verify_idx = text.index("ERROR: import-worker is not running after deploy")

    assert stop_idx < start_idx
    assert rm_idx < start_idx
    assert start_idx < verify_idx


def test_deploy_does_not_start_whole_ops_profile_new() -> None:
    text = _workflow()
    deploy_start = text.index("name: Deploy on server")
    verify_build_start = text.index("name: Verify build.json")
    deploy_section = text[deploy_start:verify_build_start]

    assert "--profile ops" not in deploy_section
    assert "docker compose up -d --no-deps import-worker" in deploy_section
    assert "docker compose up -d seed" not in deploy_section
    assert "docker compose up -d address-backfill" not in deploy_section
    assert "docker compose up -d place-enrichment-export" not in deploy_section


def test_deploy_verifies_import_worker_after_backend_ready_new() -> None:
    text = _workflow()
    ready_idx = text.index("Backend ready check passed")
    worker_verify_idx = text.index("=== Verifying import-worker runtime state ===")
    success_idx = text.index("Backend /ready and import-worker runtime checks passed.")

    assert ready_idx < worker_verify_idx < success_idx
