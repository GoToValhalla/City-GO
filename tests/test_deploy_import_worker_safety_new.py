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
    worker = _compose_services()["import-worker"]

    assert worker.get("profiles") == ["ops"]
    assert worker.get("command") == (
        'bash -c "python data/scripts/check_import_worker_resources.py '
        '&& exec python data/scripts/run_admin_import_worker.py"'
    )


def test_ops_profile_services_are_known_and_not_all_deploy_safe_new() -> None:
    services = _compose_services()
    ops_services = sorted(name for name, service in services.items() if "ops" in service.get("profiles", []))

    assert ops_services == ["address-backfill", "import-worker", "place-enrichment-export", "seed"]


def test_deploy_keeps_import_worker_stopped_after_app_up_new() -> None:
    text = _workflow()
    stop_idx = text.index("docker compose stop frontend backend import-worker bot")
    rm_idx = text.index("docker compose rm -f frontend backend import-worker bot")
    up_idx = text.index("timeout 180s docker compose up -d --remove-orphans")
    final_check_idx = text.index("Final invariant: import-worker must not be running")

    assert stop_idx < up_idx
    assert rm_idx < up_idx
    assert up_idx < final_check_idx


def test_deploy_does_not_start_whole_ops_profile_new() -> None:
    text = _workflow()
    deploy_start = text.index("name: Deploy on server")
    verify_build_start = text.index("name: Verify build.json")
    deploy_section = text[deploy_start:verify_build_start]

    assert "--profile ops" not in deploy_section
    assert "docker compose up -d --no-deps import-worker" not in deploy_section
    assert "docker compose up -d seed" not in deploy_section
    assert "docker compose up -d address-backfill" not in deploy_section
    assert "docker compose up -d place-enrichment-export" not in deploy_section


def test_deploy_explicitly_stops_import_worker_new() -> None:
    text = _workflow()
    deploy_start = text.index("name: Deploy on server")
    cleanup_start = text.index("name: Cleanup old images after confirmed healthy deploy")
    deploy_section = text[deploy_start:cleanup_start]

    assert deploy_section.count("docker compose stop frontend backend import-worker bot || true") == 1
    assert deploy_section.count("docker compose stop import-worker || true") == 1
    assert 'if [ "$WORKER_STATE" = "running" ]; then' in deploy_section


def test_deploy_verifies_import_worker_stopped_after_backend_ready_new() -> None:
    text = _workflow()
    ready_idx = text.index("Backend ready check passed")
    worker_verify_idx = text.index("Final invariant: import-worker must not be running")
    success_idx = text.index("import-worker invariant holds")

    assert ready_idx < worker_verify_idx < success_idx


def test_import_worker_has_exact_resource_contract_new() -> None:
    worker = _compose_services()["import-worker"]

    assert worker.get("restart") == "no"
    assert worker.get("mem_limit") == "512m"
    assert worker.get("memswap_limit") == "512m"
    assert worker.get("cpus") == "0.50"
    assert worker.get("stop_grace_period") == "30s"
    assert "deploy" not in worker


def test_import_worker_safe_mode_env_contract_new() -> None:
    worker = _compose_services()["import-worker"]
    env = worker.get("environment", {})

    assert str(env.get("IMPORT_WORKER_SAFE_MODE")).lower() == "true"
    # Set from the shell environment of `docker compose up` (see
    # .github/workflows/run-import-worker-safe.yml), same pattern as
    # IMPORT_WORKER_RUN_MODE/IMPORT_WORKER_CITY_SLUG: the GHA monitor loop
    # and the worker's own runtime guard must share one effective limit.
    assert env.get("IMPORT_WORKER_MAX_RUNTIME_SECONDS") == "${IMPORT_WORKER_MAX_RUNTIME_SECONDS:-900}"
    assert env.get("IMPORT_WORKER_BACKEND_HEALTH_URL") == "http://backend:8000/ready"
    assert env.get("IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB") == "${IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB:-500}"
    assert env.get("IMPORT_WORKER_MIN_JOB_CLAIM_MEMORY_MB") == "${IMPORT_WORKER_MIN_JOB_CLAIM_MEMORY_MB:-350}"
    assert env.get("IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB") == "${IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB:-512}"
    assert env.get("IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB") == "${IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB:-400}"
    assert env.get("IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB") == "${IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB:-256}"
    assert env.get("IMPORT_WORKER_RUNTIME_CGROUP_PERCENT") == "${IMPORT_WORKER_RUNTIME_CGROUP_PERCENT:-85}"
    assert env.get("IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY") == "${IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY:-1}"
    assert int(env.get("IMPORT_WORKER_BATCH_LIMIT")) == 1
