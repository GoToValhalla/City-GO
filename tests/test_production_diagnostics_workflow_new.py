"""Static contract tests for .github/workflows/production-diagnostics.yml —
a manual-only, read-only production diagnostics workflow. Confirms it never
contains a mutating docker/compose command, never runs an unformatted/full
`docker inspect` (which would expose .Config.Env), and never copies a file
to or deletes a file from the production host — it is gated the same way as
other emergency/manual workflows in this repository."""

from __future__ import annotations

import re
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

# Any actual `docker inspect <target>` invocation line (not a comment, not
# the surrounding prose) that is NOT immediately followed by --format on
# that same line or the next non-blank line (for backslash line
# continuations). A bare/unformatted inspect exposes the full container
# JSON, including .Config.Env with raw production secret values.
_INSPECT_INVOCATION_RE = re.compile(r'^\s*docker inspect\b(?!.*--format)(?!.*>/dev/null)(.*)$', re.M)

_SERVER_SIDE_FILE_PATTERNS = (
    re.compile(r'(?<![\w-])scp\b'),
    re.compile(r'(?<![\w-])sftp\b'),
    re.compile(r'(?<![\w-])rsync\b'),
    re.compile(r'/tmp/city-go-diagnostics-remote\.sh'),
    re.compile(r'rm\s+-f\s+/tmp/city-go-diagnostics-remote'),
)


def _strip_comment_lines(text: str) -> str:
    """Drop full-line `#` comments so explanatory prose (which legitimately
    names 'scp'/'sftp'/'rsync' to document what this workflow does NOT do)
    is not mistaken for an actual command invocation."""
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))


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
    redact_index = text.index("Redaction is DEFENSE IN DEPTH ONLY")
    upload_index = text.index("Upload redacted diagnostics report")
    assert redact_index < upload_index


def test_production_diagnostics_workflow_uploads_artifact_even_on_failure_new() -> None:
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    upload_step = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload_step.get("if") == "always()"


def test_production_diagnostics_workflow_public_curl_writes_to_raw_log_not_final_report_new() -> None:
    """The public health/ready curl step must append only to raw-report.log
    (pre-redaction input), never directly to production-diagnostics-
    report.txt (the final redacted artifact) -- that was the exact defect:
    raw curl output landing in the artifact after the only redaction pass
    had already run."""
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    public_step = next(s for s in steps if s.get("name", "").startswith("Check public health endpoint"))
    run_text = public_step["run"]
    assert '>> "$RAW_LOG"' in run_text
    assert "REPORT" not in run_text
    assert "production-diagnostics-report.txt" not in run_text


def test_production_diagnostics_workflow_final_redaction_runs_after_both_raw_sources_new() -> None:
    """The redaction/finalize step must be ordered after BOTH the SSH
    collection step and the public health-check step, so it is the single
    point where all raw output has already been written to raw-report.log
    before redaction reads it."""
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    names = [s.get("name", "") for s in steps]
    ssh_index = next(i for i, n in enumerate(names) if n.startswith("Collect read-only production diagnostics"))
    public_index = next(i for i, n in enumerate(names) if n.startswith("Check public health endpoint"))
    redact_index = next(i for i, n in enumerate(names) if n.startswith("Redact and finalize diagnostics report"))
    upload_index = next(i for i, n in enumerate(names) if n.startswith("Upload redacted diagnostics report"))
    assert ssh_index < redact_index
    assert public_index < redact_index
    assert redact_index < upload_index


def test_production_diagnostics_workflow_redaction_step_is_the_only_writer_of_final_report_new() -> None:
    """Only the dedicated redact/finalize step may write to
    production-diagnostics-report.txt. No other step's `run` block may
    reference that filename -- proving nothing can append to the final
    artifact after redaction has produced it."""
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    for step in steps:
        name = step.get("name", "")
        run_text = step.get("run", "")
        if "production-diagnostics-report.txt" in run_text or 'REPORT=' in run_text:
            assert name.startswith("Redact and finalize diagnostics report"), (
                f"step {name!r} references the final report file, but only the "
                "redact/finalize step is allowed to"
            )


def test_production_diagnostics_workflow_redaction_step_runs_always_new() -> None:
    """The redaction/finalize step must run even if the SSH step or the
    public health-check step failed (or raw-report.log doesn't exist yet),
    so the artifact is still produced (possibly noting partial capture)."""
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    redact_step = next(s for s in steps if s.get("name", "").startswith("Redact and finalize diagnostics report"))
    assert redact_step.get("if") == "always()"
    assert 'if [ ! -f "$RAW_LOG" ]' in redact_step["run"]


def test_production_diagnostics_workflow_artifact_path_is_the_redacted_file_only_new() -> None:
    """The uploaded artifact's `path` must point only at the final
    redacted report, never at raw-report.log or any other raw file."""
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    upload_step = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    path = upload_step["with"]["path"]
    assert path == "/tmp/city-go-diagnostics/production-diagnostics-report.txt"
    assert "raw-report.log" not in path
    assert "raw" not in path.lower()


def test_production_diagnostics_workflow_raw_log_never_printed_or_uploaded_new() -> None:
    """raw-report.log must never be uploaded as an artifact, never `cat`,
    and never appended to GITHUB_STEP_SUMMARY -- it exists only as
    redaction input. Comment lines are excluded since this workflow's own
    explanatory comments legitimately name GITHUB_STEP_SUMMARY to document
    that raw content is never written there."""
    text = _strip_comment_lines(_read())
    assert "cat \"$RAW_LOG\"" not in text
    assert "cat $RAW_LOG" not in text
    assert "GITHUB_STEP_SUMMARY" not in text
    data = _load()
    steps = data["jobs"]["diagnostics"]["steps"]
    for step in steps:
        if step.get("uses", "").startswith("actions/upload-artifact"):
            assert "raw-report.log" not in step["with"]["path"]


def test_production_diagnostics_workflow_rejects_unformatted_docker_inspect_new() -> None:
    """A `docker inspect <container>` with no --format returns the full
    container JSON, including .Config.Env — raw production secret values.
    Every inspect invocation in this workflow must use an explicit
    --format allowlist (checked as a positive contract below); this test
    fails loudly if any bare/unformatted invocation is ever reintroduced."""
    text = _read()
    offenders = [m.group(0).strip() for m in _INSPECT_INVOCATION_RE.finditer(text)]
    assert offenders == [], f"unformatted docker inspect invocation(s) found: {offenders}"


def test_production_diagnostics_workflow_never_collects_config_env_new() -> None:
    """Comment lines are excluded since this workflow's own explanatory
    comments legitimately name .Config.Env to document that it is never
    collected."""
    text = _strip_comment_lines(_read())
    assert ".Config.Env" not in text
    assert "{{json .Config}}" not in text
    assert "{{json .}}" not in text


def test_production_diagnostics_workflow_never_touches_production_filesystem_new() -> None:
    """No scp/sftp/rsync, no remote temp-script path, and no remote `rm` of
    a diagnostics artifact — the remote script must be piped over ssh's own
    stdin, never copied to and deleted from the host. Comment lines are
    excluded since this workflow's own docstring-style comments legitimately
    name these tools to document what it does NOT do."""
    text = _strip_comment_lines(_read())
    for pattern in _SERVER_SIDE_FILE_PATTERNS:
        assert not pattern.search(text), f"server-side file operation found: {pattern.pattern!r}"


def test_production_diagnostics_workflow_pipes_script_over_ssh_stdin_new() -> None:
    text = _read()
    assert "'bash -s' < \"$REMOTE_SCRIPT\"" in text
    # The local temp file is only ever removed on the RUNNER, after ssh
    # has already read it as stdin -- not on the remote host.
    runner_cleanup_index = text.index('rm -f "$REMOTE_SCRIPT"')
    ssh_index = text.index("'bash -s' < \"$REMOTE_SCRIPT\"")
    assert ssh_index < runner_cleanup_index


def test_production_diagnostics_workflow_all_inspect_calls_use_format_allowlist_new() -> None:
    """Positive contract: every docker inspect call in the workflow uses
    an explicit --format template (an allowlist of fields), never the
    full/default JSON output. The negative regex test above already
    proves no unformatted invocation exists; this asserts the specific
    allowlisted fields required for diagnosis are actually present."""
    text = _read()
    format_calls = list(re.finditer(r'docker inspect\b', text))
    assert len(format_calls) >= 5  # backend identity/state/healthcheck/network/mounts + image/container loops
    assert '{{.State.Status}}' in text
    assert '{{.State.ExitCode}}' in text
    assert '{{.State.OOMKilled}}' in text
    assert '{{range .State.Health.Log}}' in text
    assert 'org.opencontainers.image.revision' in text
    assert '{{.Config.Image}}' in text
