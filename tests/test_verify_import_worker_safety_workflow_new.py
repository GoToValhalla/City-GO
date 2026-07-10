"""Structural safety checks for the read-only import-worker safety verification workflow."""

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

FORBIDDEN_DB_SNIPPETS = (
    "psql",
    "UPDATE ",
    "DELETE FROM",
    "INSERT INTO",
)


def _workflow_text() -> str:
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _workflow_yaml() -> dict:
    data = yaml.safe_load(_workflow_text())
    assert isinstance(data, dict)
    return data


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
    assert "exit 1" in text


def test_workflow_has_no_forbidden_docker_mutation_commands_new() -> None:
    text = _workflow_text()
    # Exclude the final summary line, which only *names* these commands to
    # state they were not run — it must not itself contain a real invocation.
    summary_marker = "=== verification complete:"
    body = text.split(summary_marker)[0] if summary_marker in text else text

    for snippet in FORBIDDEN_MUTATION_SNIPPETS:
        assert snippet not in body, f"forbidden mutation command found: {snippet}"


def test_workflow_has_no_db_mutation_commands_new() -> None:
    text = _workflow_text()

    for snippet in FORBIDDEN_DB_SNIPPETS:
        assert snippet not in text, f"forbidden DB command found: {snippet}"


def test_workflow_does_not_touch_deploy_or_safe_run_workflows_new() -> None:
    """This diagnostic must be additive only — it must not modify the
    existing deploy or guarded manual run-worker workflows."""
    deploy_workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    safe_run_workflow = (ROOT / ".github" / "workflows" / "run-import-worker-safe.yml").read_text(encoding="utf-8")

    assert "verify-import-worker-safety" not in deploy_workflow
    assert "verify-import-worker-safety" not in safe_run_workflow


def test_workflow_checks_public_endpoints_and_container_state_new() -> None:
    text = _workflow_text()

    assert "/build.json" in text
    assert "/api/health" in text
    assert "/api/ready" in text
    assert "docker compose ps -a" in text
    assert "import-worker container state" in text
    assert "must NOT be running" in text


def test_workflow_reads_queue_state_without_sql_new() -> None:
    text = _workflow_text()

    assert "/admin/import-queue" in text
    assert "psql" not in text


def test_workflow_uploads_verification_artifact_new() -> None:
    data = _workflow_yaml()
    steps = data["jobs"]["verify-import-worker-safety"]["steps"]
    upload_steps = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")]

    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "import-worker-safety-verification-report"
    assert upload_steps[0].get("if") == "always()"


def test_workflow_uses_robust_json_compose_config_extraction_new() -> None:
    """The fragile sed-based section-boundary extraction must be replaced with
    a robust `docker compose config --format json` + Python parse, since sed
    boundary matching against arbitrary YAML formatting produced an empty
    section in production."""
    text = _workflow_text()

    assert "docker compose config --format json" in text
    assert "sed -n '/^  import-worker:/" not in text


def test_workflow_validates_all_required_safety_fields_new() -> None:
    text = _workflow_text()

    for expected_field in (
        "mem_limit",
        "memswap_limit",
        "cpus",
        "restart",
        "profiles",
        "IMPORT_WORKER_SAFE_MODE",
        "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY",
        "IMPORT_WORKER_MAX_RUNTIME_SECONDS",
        "IMPORT_WORKER_BACKEND_HEALTH_URL",
        "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB",
    ):
        assert expected_field in text, f"missing validation for {expected_field}"


def test_workflow_fails_clearly_on_config_mismatch_new() -> None:
    """The remote script must propagate a non-zero exit when validation fails,
    so the GitHub Actions step (and therefore the whole run) fails clearly —
    not just print an error and continue as if everything passed."""
    text = _workflow_text()

    assert 'if [ "$CONFIG_FAIL" -ne 0 ]; then' in text
    assert "exit 1" in text
    # The failure must happen inside the remote heredoc (so it propagates
    # through the local `ssh ... | tee` pipeline via `pipefail`), not only
    # as a local echo with no effect on the step's exit code.
    remote_start = text.index("bash <<'REMOTE_EOF'")
    remote_end = text.index("REMOTE_EOF", remote_start + len("bash <<'REMOTE_EOF'"))
    remote_body = text[remote_start:remote_end]
    assert 'if [ "$CONFIG_FAIL" -ne 0 ]; then' in remote_body


def _extract_embedded_validation_script() -> str:
    # Extract via the parsed YAML `run: |` block scalar value, not the raw
    # file text — YAML has already stripped the block's common leading
    # indentation from every line (including both heredoc terminators,
    # which sit at exactly that common indentation so bash receives them
    # at column 0). The nested Python body still carries its own remaining
    # indentation relative to the surrounding bash `if/else`, so dedent it
    # by its own common leading-space prefix before running it standalone.
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


def test_embedded_validation_passes_for_correct_production_config_new() -> None:
    result = _run_validation_against_fixture({
        "profiles": ["ops"],
        "restart": "no",
        "mem_limit": 384 * 1024 * 1024,
        "memswap_limit": 384 * 1024 * 1024,
        "cpus": 0.5,
        "environment": {
            "IMPORT_WORKER_SAFE_MODE": "true",
            "IMPORT_WORKER_MAX_RUNTIME_SECONDS": "300",
            "IMPORT_WORKER_BACKEND_HEALTH_URL": "http://backend:8000/ready",
            "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB": "256",
            "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY": "0",
        },
    })

    assert result.returncode == 0, result.stderr
    assert "All import-worker safety config checks passed." in result.stdout


def test_embedded_validation_fails_for_wrong_config_new() -> None:
    result = _run_validation_against_fixture({
        "profiles": ["ops"],
        "restart": "unless-stopped",
        "environment": {"IMPORT_WORKER_SAFE_MODE": "false"},
    })

    assert result.returncode != 0
    assert "MISMATCH: restart" in result.stdout
    assert "MISMATCH: mem_limit" in result.stdout
    assert "MISMATCH: IMPORT_WORKER_SAFE_MODE" in result.stdout


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
    """Execute the EXACT script as YAML parses it (both heredocs still
    nested exactly as written), not an independently re-dedented Python
    fragment. `ssh ...` is swapped for a local `bash` (same heredoc
    document) and `docker compose config --format json` is swapped for a
    `cat` of a pre-seeded fixture file, so the full chain — outer REMOTE_EOF
    heredoc, then the nested PYEOF python heredoc exactly as bash/YAML
    deliver it — runs for real, proving `import json` lands at column 0
    with no IndentationError anywhere in the pipeline."""
    data = _workflow_yaml()
    steps = data["jobs"]["verify-import-worker-safety"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == "Collect read-only verification evidence")

    with tempfile.TemporaryDirectory() as tmp:
        fixture_path = Path(tmp) / "compose-config.json"
        fixture_path.write_text(
            json.dumps({
                "services": {
                    "import-worker": {
                        "profiles": ["ops"],
                        "restart": "no",
                        "mem_limit": 384 * 1024 * 1024,
                        "memswap_limit": 384 * 1024 * 1024,
                        "cpus": 0.5,
                        "environment": {
                            "IMPORT_WORKER_SAFE_MODE": "true",
                            "IMPORT_WORKER_MAX_RUNTIME_SECONDS": "300",
                            "IMPORT_WORKER_BACKEND_HEALTH_URL": "http://backend:8000/ready",
                            "IMPORT_WORKER_MIN_AVAILABLE_MEMORY_MB": "256",
                            "IMPORT_WORKER_MAX_FULL_IMPORT_PLACES_LOW_MEMORY": "0",
                        },
                    }
                }
            }),
            encoding="utf-8",
        )

        # Neutralize the real docker producer command FIRST (while the path
        # is still the literal /tmp/compose-config.json), replacing it with
        # a no-op that succeeds without touching the file, so the
        # subsequent path substitution points every *reader* at the
        # pre-seeded fixture while the fixture itself is never overwritten.
        patched = script.replace(
            "docker compose config --format json > /tmp/compose-config.json 2>/tmp/compose-config.err",
            "true 2>/tmp/compose-config.err",
        )
        patched = patched.replace("/tmp/compose-config.json", str(fixture_path))
        # Replace only the ssh invocation with a local bash — the heredoc
        # document (REMOTE_EOF ... including the nested PYEOF block) is
        # left completely untouched, exactly as GitHub Actions would feed it.
        ssh_start = patched.index("ssh \\")
        ssh_end = patched.index("bash <<'REMOTE_EOF'")
        patched = patched[:ssh_start] + patched[ssh_end:]

        script_path = Path(tmp) / "run_script.sh"
        script_path.write_text(patched, encoding="utf-8")
        result = subprocess.run(["bash", str(script_path)], capture_output=True, text=True)

    assert "IndentationError" not in result.stdout
    assert "IndentationError" not in result.stderr
    assert "import json" not in result.stderr
    assert "All import-worker safety config checks passed." in result.stdout
    assert "=== verification complete:" in result.stdout
    assert result.returncode == 0, result.stderr
