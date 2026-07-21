"""Static contract tests for .github/workflows/production-diagnostics.yml —
a manual-only, read-only production diagnostics workflow. Confirms it never
contains a mutating docker/compose command and is gated the same way as
other emergency/manual workflows in this repository."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/production-diagnostics.yml"

_FORBIDDEN_SUBSTRINGS = (
    "docker compose up",
    "docker compose down",
    "docker compose restart",
    "docker compose stop",
    "docker compose start",
    "docker compose rm",
    "docker compose kill",
    "docker compose recreate",
    "docker start ",
    "docker stop ",
    "docker restart ",
    "docker rm ",
    "docker kill ",
    "docker load",
    "alembic upgrade",
    "alembic downgrade",
    " > /srv/app/.env",
    ">> /srv/app/.env",
    " > /srv/app/.last_deployed_sha",
    ">> /srv/app/.last_deployed_sha",
)


def _read() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _load() -> dict:
    return yaml.safe_load(_read())


def test_production_diagnostics_workflow_is_valid_yaml_new() -> None:
    data = _load()
    assert data.get("name") == "99 · CITY GO · Production Diagnostics"
    assert "jobs" in data


def test_production_diagnostics_workflow_only_trigger_is_workflow_dispatch_new() -> None:
    data = _load()
    on_block = data.get(True, data.get("on"))
    assert list(on_block.keys()) == ["workflow_dispatch"]


def test_production_diagnostics_workflow_requires_exact_confirmation_new() -> None:
    data = _load()
    on_block = data.get(True, data.get("on"))
    inputs = on_block["workflow_dispatch"]["inputs"]
    assert inputs["confirmation"]["required"] is True

    text = _read()
    assert 'inputs.confirmation }}" != "RUN_READ_ONLY_PRODUCTION_DIAGNOSTICS"' in text
    assert "exit 1" in text


def test_production_diagnostics_workflow_contains_no_mutating_commands_new() -> None:
    text = _read()
    for forbidden in _FORBIDDEN_SUBSTRINGS:
        assert forbidden not in text, f"forbidden mutating pattern found: {forbidden!r}"


def test_production_diagnostics_workflow_captures_backend_logs_and_inspect_new() -> None:
    text = _read()
    assert "docker inspect app-backend-1" in text
    assert "docker logs --timestamps --tail 1000 app-backend-1" in text
    assert "docker compose logs --timestamps --tail 1000 backend" in text
    assert "docker compose logs --timestamps --tail 300 migrate" in text


def test_production_diagnostics_workflow_reads_last_deployed_sha_readonly_new() -> None:
    text = _read()
    assert "cat /srv/app/.last_deployed_sha" in text


def test_production_diagnostics_workflow_checks_internal_and_public_health_new() -> None:
    text = _read()
    assert "curl -i --max-time 10 http://localhost:8000/health" in text
    assert "curl -i --max-time 10 http://localhost:8000/ready" in text
    assert '"${BASE_URL}/api/health"' in text
    assert '"${BASE_URL}/api/ready"' in text


def test_production_diagnostics_workflow_redacts_before_upload_new() -> None:
    text = _read()
    assert "REDACTED" in text
    # Redaction must run (and complete) before the artifact upload step.
    redact_index = text.index("Redact secrets")
    upload_index = text.index("Upload redacted diagnostics report")
    assert redact_index < upload_index


def test_production_diagnostics_workflow_uploads_artifact_even_on_failure_new() -> None:
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    upload_step = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload_step.get("if") == "always()"
