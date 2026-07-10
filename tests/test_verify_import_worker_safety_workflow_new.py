"""Structural safety checks for the read-only import-worker safety verification workflow."""

from __future__ import annotations

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
