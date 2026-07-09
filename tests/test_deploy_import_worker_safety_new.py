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


def test_deploy_keeps_import_worker_stopped_after_app_up_new() -> None:
    text = _workflow()
    stop_idx = text.index("docker compose stop frontend backend import-worker bot")
    rm_idx = text.index("docker compose rm -f frontend backend import-worker bot")
    up_idx = text.index("timeout 180s docker compose up -d --remove-orphans")
    ensure_idx = text.index("=== Ensure import-worker stays stopped after deploy ===")
    verify_idx = text.index("ERROR: import-worker is running after deploy")

    assert stop_idx < up_idx
    assert rm_idx < up_idx
    assert up_idx < ensure_idx < verify_idx


def test_deploy_does_not_start_whole_ops_profile_new() -> None:
    text = _workflow()
    deploy_start = text.index("name: Deploy on server")
    verify_build_start = text.index("name: Verify build.json")
    deploy_section = text[deploy_start:verify_build_start]

    assert "--profile ops" not in deploy_section
    assert "timeout 120s docker compose up -d --no-deps import-worker" not in text
    assert "docker compose up -d --no-deps import-worker" not in deploy_section
    assert "docker compose up -d seed" not in deploy_section
    assert "docker compose up -d address-backfill" not in deploy_section
    assert "docker compose up -d place-enrichment-export" not in deploy_section


def test_deploy_explicitly_stops_import_worker_new() -> None:
    text = _workflow()
    deploy_start = text.index("name: Deploy on server")
    cleanup_start = text.index("name: Cleanup old images after confirmed healthy deploy")
    deploy_section = text[deploy_start:cleanup_start]

    assert deploy_section.count("docker compose stop import-worker || true") == 2
    assert 'if [ "$WORKER_STATE" = "running" ]; then' in deploy_section
    assert 'if [ "$WORKER_STATE" != "running" ]; then' not in deploy_section


def test_deploy_verifies_import_worker_stopped_after_backend_ready_new() -> None:
    text = _workflow()
    ready_idx = text.index("Backend ready check passed")
    worker_verify_idx = text.index("=== Verifying import-worker remains stopped ===")
    success_idx = text.index("Backend /ready passed and import-worker is not running")

    assert ready_idx < worker_verify_idx < success_idx


def test_import_worker_has_hard_resource_limits_new() -> None:
    """Post-OOM-incident safety: import-worker must never be able to consume
    unbounded host memory/CPU again, and must never crash-loop."""
    services = _compose_services()
    worker = services["import-worker"]

    assert worker.get("mem_limit") is not None
    assert worker.get("cpus") is not None
    assert worker.get("restart") == "no"


def test_import_worker_mem_limit_is_plain_compose_syntax_new() -> None:
    """Must use plain `docker compose` service keys (mem_limit/cpus), not the
    Swarm-only `deploy.resources` block, since this deployment does not use Swarm."""
    services = _compose_services()
    worker = services["import-worker"]

    assert "deploy" not in worker
    assert isinstance(worker.get("mem_limit"), str)
    assert worker["mem_limit"].endswith("m")


def test_import_worker_safe_mode_env_defaults_are_set_new() -> None:
    services = _compose_services()
    worker = services["import-worker"]
    env = worker.get("environment", {})

    assert str(env.get("IMPORT_WORKER_SAFE_MODE")).lower() == "true"
    assert int(env.get("IMPORT_WORKER_MAX_RUNTIME_SECONDS")) > 0
    assert env.get("IMPORT_WORKER_BACKEND_HEALTH_URL")
    assert int(env.get("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB")) > 0
    assert int(env.get("IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY")) == 0
