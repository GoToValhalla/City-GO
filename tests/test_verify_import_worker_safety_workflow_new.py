"""Structural safety checks for the read-only import-worker diagnostic workflow."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "verify-import-worker-safety.yml"

FORBIDDEN_MUTATION_SNIPPETS = (
    "docker compose up",
    "docker compose start",
    "docker compose restart",
    "docker compose stop",
    "docker pull",
    "docker rm",
    "docker rmi",
)
FORBIDDEN_DB_SNIPPETS = ("psql", "UPDATE ", "DELETE FROM", "INSERT INTO")


def _workflow_text() -> str:
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _workflow_yaml() -> dict:
    data = yaml.safe_load(_workflow_text())
    assert isinstance(data, dict)
    return data


def _fixture_service() -> dict:
    return {
        "profiles": ["ops"],
        "restart": "no",
        "command": "bash -c python data/scripts/check_import_worker_resources.py && exec python data/scripts/run_admin_import_worker.py",
        "mem_limit": 512 * 1024 * 1024,
        "memswap_limit": 512 * 1024 * 1024,
        "cpus": 0.5,
        "environment": {
            "IMPORT_WORKER_SAFE_MODE": "true",
            "IMPORT_WORKER_MAX_RUNTIME_SECONDS": "300",
            "IMPORT_WORKER_BACKEND_HEALTH_URL": "http://backend:8000/ready",
            "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB": "550",
            "IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB": "512",
            "IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB": "400",
            "IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB": "256",
            "IMPORT_WORKER_RUNTIME_CGROUP_PERCENT": "85",
            "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY": "1",
            "IMPORT_WORKER_BATCH_LIMIT": "1",
        },
    }


def test_workflow_is_manual_dispatch_only_new() -> None:
    data = _workflow_yaml()
    triggers = data.get(True) or data.get("on")

    assert isinstance(triggers, dict)
    assert "workflow_dispatch" in triggers
    assert "schedule" not in triggers
    assert "push" not in triggers
    assert "pull_request" not in triggers


def test_workflow_requires_exact_confirmation_new() -> None:
    text = _workflow_text()

    assert "VERIFY_IMPORT_WORKER_SAFETY" in text
    assert 'if [ "${{ inputs.confirmation }}" != "VERIFY_IMPORT_WORKER_SAFETY" ]; then' in text


def test_workflow_has_no_forbidden_mutations_new() -> None:
    text = _workflow_text()
    summary_marker = "=== verification complete:"
    body = text.split(summary_marker)[0] if summary_marker in text else text

    for snippet in FORBIDDEN_MUTATION_SNIPPETS:
        assert snippet not in body, f"forbidden mutation command found: {snippet}"
    for snippet in FORBIDDEN_DB_SNIPPETS:
        assert snippet not in text, f"forbidden DB command found: {snippet}"


def test_workflow_checks_public_endpoints_container_and_queue_new() -> None:
    text = _workflow_text()

    assert "/build.json" in text
    assert "/api/health" in text
    assert "/api/ready" in text
    assert "docker compose ps -a" in text
    assert "import-worker container state" in text
    assert "must NOT be running" in text
    assert "/admin/import-queue" in text


def test_workflow_uploads_verification_artifact_new() -> None:
    data = _workflow_yaml()
    steps = data["jobs"]["verify-import-worker-safety"]["steps"]
    upload_steps = [step for step in steps if step.get("uses", "").startswith("actions/upload-artifact")]

    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "import-worker-safety-verification-report"
    assert upload_steps[0].get("if") == "always()"


def test_workflow_uses_json_compose_config_extraction_new() -> None:
    text = _workflow_text()

    assert "docker compose config --format json" in text
    assert "sed -n '/^  import-worker:/" not in text


def test_workflow_enables_ops_profile_for_compose_config_new() -> None:
    """import-worker is defined behind `profiles: ["ops"]` in
    docker-compose.yml, so `docker compose config` must explicitly enable
    that profile — otherwise the effective config never includes the
    import-worker service at all, and the embedded Python validation fails
    with "import-worker service not found in effective compose config"
    even though the service is correctly defined and running. This is a
    real regression observed in production (workflow run 29182836886):
    the diagnostic itself failed, not the worker."""
    text = _workflow_text()

    assert "docker compose --profile ops config --format json" in text


def test_import_worker_profile_membership_matches_workflow_assumption_new() -> None:
    """Guards against the opposite drift: if import-worker were ever moved
    out of the `ops` profile in docker-compose.yml, this workflow's
    `--profile ops` flag would become unnecessary but harmless — this test
    exists so a future change to docker-compose.yml's profile assignment is
    forced to revisit this workflow instead of silently diverging."""
    compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    compose = yaml.safe_load(compose_text)
    import_worker = compose["services"]["import-worker"]

    assert import_worker.get("profiles") == ["ops"]


def test_workflow_validates_full_recalibrated_contract_new() -> None:
    text = _workflow_text()

    for expected_field in (
        "mem_limit",
        "memswap_limit",
        "cpus",
        "restart",
        "profiles",
        "command",
        "IMPORT_WORKER_SAFE_MODE",
        "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY",
        "IMPORT_WORKER_MAX_RUNTIME_SECONDS",
        "IMPORT_WORKER_BACKEND_HEALTH_URL",
        "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB",
        "IMPORT_WORKER_MIN_CONTAINER_MEMORY_MB",
        "IMPORT_WORKER_MIN_CONTAINER_HEADROOM_MB",
        "IMPORT_WORKER_RUNTIME_HOST_FLOOR_MB",
        "IMPORT_WORKER_RUNTIME_CGROUP_PERCENT",
        "IMPORT_WORKER_BATCH_LIMIT",
    ):
        assert expected_field in text, f"missing validation for {expected_field}"

    assert "512m (536870912 bytes)" in text
    assert '"IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB": "550"' in text
    assert '"IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY": "1"' in text


def test_workflow_fails_clearly_on_config_mismatch_new() -> None:
    text = _workflow_text()

    assert 'if [ "$CONFIG_FAIL" -ne 0 ]; then' in text
    remote_start = text.index("bash <<'REMOTE_EOF'")
    remote_end = text.index("REMOTE_EOF", remote_start + len("bash <<'REMOTE_EOF'"))
    remote_body = text[remote_start:remote_end]
    assert 'if [ "$CONFIG_FAIL" -ne 0 ]; then' in remote_body
    assert "exit 1" in remote_body


def _extract_embedded_validation_script() -> str:
    data = _workflow_yaml()
    steps = data["jobs"]["verify-import-worker-safety"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Collect read-only verification evidence")
    match = re.search(r"python3 - <<'PYEOF'.*?\n(.*?)\nPYEOF", script, re.S)
    assert match is not None, "embedded PYEOF python block not found"
    body = match.group(1)
    lines = body.split("\n")
    non_blank = [line for line in lines if line.strip()]
    indent = min((len(line) - len(line.lstrip(" ")) for line in non_blank), default=0)
    return "\n".join(line[indent:] if line.startswith(" " * indent) else line for line in lines)


def _run_validation_against_fixture(service_config: dict) -> subprocess.CompletedProcess:
    script = _extract_embedded_validation_script()
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "compose-config.json"
        config_path.write_text(json.dumps({"services": {"import-worker": service_config}}), encoding="utf-8")
        patched = script.replace("/tmp/compose-config.json", str(config_path))
        script_path = Path(tmp) / "check.py"
        script_path.write_text(patched, encoding="utf-8")
        return subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)


def test_embedded_validation_passes_for_recalibrated_config_new() -> None:
    result = _run_validation_against_fixture(_fixture_service())

    assert result.returncode == 0, result.stderr
    assert "All import-worker safety config checks passed." in result.stdout


def test_embedded_validation_fails_for_old_low_memory_contract_new() -> None:
    old = _fixture_service()
    old.update({"mem_limit": 384 * 1024 * 1024, "memswap_limit": 384 * 1024 * 1024})
    old["environment"] = dict(old["environment"])
    old["environment"].update({
        "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB": "256",
        "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY": "0",
    })

    result = _run_validation_against_fixture(old)

    assert result.returncode != 0
    assert "MISMATCH: mem_limit" in result.stdout
    assert "MISMATCH: IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB" in result.stdout
    assert "MISMATCH: IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY" in result.stdout


def test_embedded_validation_fails_when_service_missing_new() -> None:
    script = _extract_embedded_validation_script()
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "compose-config.json"
        config_path.write_text(json.dumps({"services": {}}), encoding="utf-8")
        patched = script.replace("/tmp/compose-config.json", str(config_path))
        script_path = Path(tmp) / "check.py"
        script_path.write_text(patched, encoding="utf-8")
        result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)

    assert result.returncode != 0
    assert "import-worker service not found" in result.stderr


def test_end_to_end_parsed_run_script_nested_python_has_no_indentation_error_new() -> None:
    data = _workflow_yaml()
    steps = data["jobs"]["verify-import-worker-safety"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Collect read-only verification evidence")

    with tempfile.TemporaryDirectory() as tmp:
        fixture_path = Path(tmp) / "compose-config.json"
        fixture_path.write_text(
            json.dumps({"services": {"import-worker": _fixture_service()}}),
            encoding="utf-8",
        )
        patched = script.replace(
            "docker compose --profile ops config --format json > /tmp/compose-config.json 2>/tmp/compose-config.err",
            "true 2>/tmp/compose-config.err",
        )
        patched = patched.replace("/tmp/compose-config.json", str(fixture_path))
        ssh_start = patched.index("ssh \\")
        ssh_end = patched.index("bash <<'REMOTE_EOF'")
        patched = patched[:ssh_start] + patched[ssh_end:]

        # Neutralize external/read-only commands; preserve both heredocs and the
        # exact embedded Python validation path.
        for command in (
            "curl -sS -o /dev/null -w 'HTTP=%{http_code}\\n' --max-time 15",
            "docker compose ps -a",
            "docker compose ps -aq import-worker",
            "docker stats --no-stream",
            "free -h",
            "df -h",
            "docker compose logs --tail=100 backend",
            "docker compose logs --tail=100 import-worker",
            "docker compose logs --tail=100 frontend",
        ):
            patched = patched.replace(command, "true")
        patched = patched.replace("cd /srv/app", "true")

        script_path = Path(tmp) / "run_script.sh"
        script_path.write_text(patched, encoding="utf-8")
        result = subprocess.run(["bash", str(script_path)], capture_output=True, text=True)

    assert "IndentationError" not in result.stdout
    assert "IndentationError" not in result.stderr
    assert "All import-worker safety config checks passed." in result.stdout
    assert "=== verification complete:" in result.stdout
    assert result.returncode == 0, result.stderr
