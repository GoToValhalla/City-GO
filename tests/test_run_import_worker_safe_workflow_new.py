"""Structural safety checks for the manual guarded import-worker run workflow."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "run-import-worker-safe.yml"


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


def test_workflow_uses_typed_run_mode_input_not_free_text_confirmation_new() -> None:
    """The old free-text RUN_IMPORT_WORKER_SAFELY confirmation input is
    replaced by a typed run_mode choice input, so the UI presents a fixed
    set of valid actions instead of requiring an operator to type an exact
    magic string."""
    data = _workflow_yaml()
    inputs = data[True]["workflow_dispatch"]["inputs"]

    assert "confirmation" not in inputs
    assert "RUN_IMPORT_WORKER_SAFELY" not in _workflow_text()

    run_mode = inputs["run_mode"]
    assert run_mode["type"] == "choice"
    assert run_mode["default"] == "safe_one_job"
    assert set(run_mode["options"]) == {"safe_one_job", "dry_run", "diagnostics_only"}

    city_slug = inputs["city_slug"]
    assert city_slug["required"] is False


def test_workflow_validates_run_mode_value_new() -> None:
    text = _workflow_text()

    assert "safe_one_job|dry_run|diagnostics_only" in text
    assert "run_mode must be one of safe_one_job, dry_run, diagnostics_only" in text


def test_workflow_preflight_checks_health_memory_and_running_state_new() -> None:
    text = _workflow_text()

    assert "preflight: public health/ready" in text
    assert "preflight: host memory" in text
    assert "STARTUP_HOST_FLOOR_MB=550" in text
    assert "preflight: import-worker must not already be running" in text
    assert "PREFLIGHT FAILED" in text


def test_workflow_starts_only_import_worker_not_whole_ops_profile_new() -> None:
    text = _workflow_text()

    assert "docker compose up -d --no-deps --force-recreate import-worker" in text
    assert "--profile ops" not in text
    assert "docker compose up -d seed" not in text
    assert "docker compose up -d address-backfill" not in text
    assert "docker compose up -d place-enrichment-export" not in text


def test_workflow_has_runtime_host_cgroup_and_health_guards_new() -> None:
    text = _workflow_text()

    assert "RUNTIME_HOST_FLOOR_MB=256" in text
    assert "RUNTIME_CGROUP_PERCENT=85" in text
    assert "public_health_degraded" in text
    assert "host_memory_floor" in text
    assert "worker_cgroup_soft_limit" in text
    assert "worker_memory_reading_unknown" in text
    assert "docker stats --no-stream" in text
    assert "worker_oom_killed" in text
    assert '"137"' in text


def test_workflow_fails_closed_on_timeout_and_bad_exit_state_new() -> None:
    text = _workflow_text()

    assert "max_runtime_reached" in text
    assert "worker exit code is unknown; failing closed" in text
    assert 'if [ "$WORKER_EXIT_CODE" -ne 0 ]; then' in text
    assert "worker run ended by safety guard" in text


def test_workflow_always_stops_worker_in_cleanup_new() -> None:
    text = _workflow_text()
    monitor_loop_start = text.index('section "monitor loop"')
    cleanup_call_idx = text.index("\n          cleanup\n", monitor_loop_start)
    trap_clear_idx = text.index("trap - EXIT", cleanup_call_idx)

    assert monitor_loop_start < cleanup_call_idx < trap_clear_idx
    assert "cleanup: always stop and remove import-worker" in text
    assert "docker compose stop -t 30 import-worker" in text
    assert "docker compose rm -f import-worker" in text
    assert "trap cleanup EXIT" in text


def test_workflow_uploads_run_report_artifact_new() -> None:
    data = _workflow_yaml()
    steps = data["jobs"]["run-import-worker-safe"]["steps"]
    upload_steps = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")]

    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "safe-import-worker-run-report"
    assert upload_steps[0].get("if") == "always()"


def test_workflow_never_deploys_pulls_images_or_mutates_db_new() -> None:
    text = _workflow_text()

    assert "docker load" not in text
    assert "docker pull" not in text
    assert "psql" not in text
    assert "UPDATE " not in text
    assert "docker compose up -d --remove-orphans" not in text


def test_workflow_uses_github_provided_values_not_github_api_new() -> None:
    text = _workflow_text()

    assert "github.run_id" in text
    assert "github.server_url" in text
    assert "github.repository" in text
    assert "github.workflow" in text
    assert "api.github.com" not in text


def test_workflow_reports_all_required_lifecycle_events_new() -> None:
    """worker_job_claimed is intentionally reported by the existing Python
    worker (_log_worker_decision inside run_queued_import_jobs, the exact
    moment a job is actually claimed) rather than re-derived here from
    workflow-side queue polling — that stays the single source of truth for
    the claim event. This workflow reports the remaining lifecycle events
    that only it can observe (process start/stop, health checks, cleanup)."""
    text = _workflow_text()

    for event in (
        "worker_run_started",
        "worker_health_check_failed",
        "worker_stop_requested",
        "worker_run_finished",
        "workflow_cleanup",
    ):
        assert f'"{event}"' in text, f"missing lifecycle event report: {event}"


def test_workflow_posts_worker_events_to_existing_backend_endpoint_new() -> None:
    text = _workflow_text()

    assert "/api/admin/system-logs/worker-event" in text
    assert "Authorization: Bearer ${ADMIN_API_TOKEN}" in text


def test_workflow_only_associates_job_id_when_actually_claimed_new() -> None:
    text = _workflow_text()

    assert 'CLAIMED_JOB_ID=""' in text
    assert "refresh_claimed_job_id" in text
    assert "running_job_ids" in text
    job_field_idx = text.index('job_field="\\"job_id\\":')
    condition_idx = text.rindex('if [ -n "${CLAIMED_JOB_ID:-}" ]; then', 0, job_field_idx)
    assert condition_idx < job_field_idx


def test_workflow_health_degradation_reports_stop_reason_new() -> None:
    text = _workflow_text()

    assert '"worker_health_check_failed"' in text
    health_report_idx = text.index('report_worker_event "worker_health_check_failed"')
    assert "stop_reason" in text[health_report_idx : health_report_idx + 200]


def test_workflow_stop_requested_and_cleanup_report_stop_reason_new() -> None:
    text = _workflow_text()

    cleanup_fn_idx = text.index("cleanup() {")
    cleanup_body = text[cleanup_fn_idx : cleanup_fn_idx + 300]
    assert 'report_worker_event "workflow_cleanup"' in cleanup_body
    assert "stop_reason" in cleanup_body
    assert text.count('report_worker_event "worker_stop_requested"') >= 5


def test_remote_ssh_variables_are_shell_quoted_not_bare_words_new() -> None:
    """Regression: WORKFLOW_NAME (github.workflow) is
    "CITY GO · OPS · Run Import Worker Safely" — spaces and Unicode. The SSH
    command used to pass each NAME="$VALUE" as a separate argv word to
    `ssh host word1 word2 ...`; ssh rejoins all trailing words with a single
    space before the remote shell re-parses them, so the remote shell saw
    WORKFLOW_NAME=CITY GO · ... and tried to run "GO" as a command
    ("bash: GO: command not found"). Every remote-bound variable must now be
    shell-quoted with printf '%q' and assembled into ONE string passed to
    ssh, matching the pattern already used for ADMIN_API_TOKEN in
    production-health.yml."""
    text = _workflow_text()

    for var in (
        "MAX_RUNTIME_SECONDS", "ADMIN_API_TOKEN", "WORKFLOW_NAME", "WORKFLOW_RUN_ID",
        "WORKFLOW_RUN_URL", "RUN_MODE", "CITY_SLUG",
    ):
        assert f"REMOTE_{var}=$(printf '%q' \"${var}\")" in text, f"{var} must be shell-quoted via printf '%q' before being sent over ssh"

    # The NAME="$VALUE" assignments and `bash -s` must be a single quoted
    # string argument to ssh, not bare trailing argv words.
    ssh_call_idx = text.index("ssh \\\n")
    single_command_idx = text.index(
        '"MAX_RUNTIME_SECONDS=$REMOTE_MAX_RUNTIME_SECONDS '
        "ADMIN_API_TOKEN=$REMOTE_ADMIN_API_TOKEN "
        "WORKFLOW_NAME=$REMOTE_WORKFLOW_NAME "
        "WORKFLOW_RUN_ID=$REMOTE_WORKFLOW_RUN_ID "
        "WORKFLOW_RUN_URL=$REMOTE_WORKFLOW_RUN_URL "
        "RUN_MODE=$REMOTE_RUN_MODE "
        'CITY_SLUG=$REMOTE_CITY_SLUG bash -s"'
    )
    assert ssh_call_idx < single_command_idx

    # The old, broken bare-word form must not reappear.
    assert 'WORKFLOW_NAME="$WORKFLOW_NAME" \\' not in text
    assert '"$SSH_USER@$SSH_HOST" \\\n            MAX_RUNTIME_SECONDS="$MAX_RUNTIME_SECONDS"' not in text


def test_remote_ssh_variables_survive_a_real_shell_roundtrip_new() -> None:
    """Behavioral proof, not just a text match: extract the exact
    printf '%q' quoting lines and the exact single-string ssh command from
    the workflow, then actually run them in bash — with a real
    WORKFLOW_NAME containing spaces and the literal '·' Unicode character —
    and confirm the value a remote shell would see is byte-for-byte
    unchanged. `eval` on the built command string here plays the same role
    ssh plays for real: ssh sends the one already-built string to the
    remote sshd, which hands it to the login shell for parsing exactly as
    eval parses it locally."""
    text = _workflow_text()

    quoting_lines = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("REMOTE_") and "printf '%q'" in line
    )
    assert quoting_lines, "could not find the printf '%q' quoting lines in the workflow"

    single_command_start = text.index('"MAX_RUNTIME_SECONDS=$REMOTE_MAX_RUNTIME_SECONDS')
    single_command_end = text.index('bash -s"', single_command_start) + len('bash -s"')
    ssh_command_literal = text[single_command_start:single_command_end]

    script = f"""
set -euo pipefail
MAX_RUNTIME_SECONDS="300"
ADMIN_API_TOKEN="abc def'ghi\\$xyz"
WORKFLOW_NAME="CITY GO · OPS · Run Import Worker Safely"
WORKFLOW_RUN_ID="123456"
WORKFLOW_RUN_URL="https://github.com/org/repo/actions/runs/123456"
RUN_MODE="safe_one_job"
CITY_SLUG="astrakhan"

{quoting_lines}

CMD={ssh_command_literal}
eval "$CMD" <<'REMOTE_EOF'
echo "NAME=[$WORKFLOW_NAME]"
echo "TOKEN=[$ADMIN_API_TOKEN]"
echo "RUNTIME=[$MAX_RUNTIME_SECONDS]"
echo "RUN_ID=[$WORKFLOW_RUN_ID]"
echo "RUN_URL=[$WORKFLOW_RUN_URL]"
echo "RUN_MODE=[$RUN_MODE]"
echo "CITY_SLUG=[$CITY_SLUG]"
REMOTE_EOF
"""
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"
    assert "NAME=[CITY GO · OPS · Run Import Worker Safely]" in result.stdout
    assert "TOKEN=[abc def'ghi$xyz]" in result.stdout
    assert "RUNTIME=[300]" in result.stdout
    assert "RUN_ID=[123456]" in result.stdout
    assert "RUN_URL=[https://github.com/org/repo/actions/runs/123456]" in result.stdout
    assert "RUN_MODE=[safe_one_job]" in result.stdout
    assert "CITY_SLUG=[astrakhan]" in result.stdout
    # The historical failure mode: "GO" being run as a command.
    assert "GO: command not found" not in result.stderr
    assert "command not found" not in result.stderr


def test_workflow_passes_run_mode_and_city_slug_to_docker_compose_up_new() -> None:
    """run_mode/city_slug must reach the import-worker container via
    IMPORT_WORKER_RUN_MODE/IMPORT_WORKER_CITY_SLUG env vars on the exact
    `docker compose up` invocation that starts it — otherwise the typed
    inputs would be accepted by the workflow UI but silently ignored."""
    text = _workflow_text()

    assert (
        'IMPORT_WORKER_RUN_MODE="$RUN_MODE" IMPORT_WORKER_CITY_SLUG="$CITY_SLUG" '
        "timeout 60s docker compose up -d --no-deps --force-recreate import-worker"
    ) in text


def test_workflow_defaults_run_mode_and_city_slug_inside_remote_script_new() -> None:
    """RUN_MODE/CITY_SLUG must be defaulted with ${VAR:-...} before use
    inside the remote heredoc, which runs under `set -uo pipefail` —
    an unset/empty value must not crash the script (regression: this
    previously failed with 'RUN_MODE: unbound variable')."""
    text = _workflow_text()

    assert 'RUN_MODE="${RUN_MODE:-safe_one_job}"' in text
    assert 'CITY_SLUG="${CITY_SLUG:-}"' in text


def test_docker_compose_import_worker_reads_run_mode_and_city_slug_from_shell_env_new() -> None:
    """docker-compose.yml must interpolate IMPORT_WORKER_RUN_MODE/
    IMPORT_WORKER_CITY_SLUG from the shell environment of the `docker
    compose up` invocation (not hardcode them), so each manual workflow
    run can select its own mode/city without editing the compose file."""
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "IMPORT_WORKER_RUN_MODE: ${IMPORT_WORKER_RUN_MODE:-safe_one_job}" in compose
    assert "IMPORT_WORKER_CITY_SLUG: ${IMPORT_WORKER_CITY_SLUG:-}" in compose


def test_stale_container_is_removed_not_just_stopped_before_recreate_new() -> None:
    """Regression: a leftover stopped import-worker container from a prior
    run (e.g. one where CITY_SLUG was empty or a different city) could be
    reused as-is by a later `docker compose up` instead of recreated with
    the new run's env vars — this is how CITY_SLUG previously reached the
    worker as empty for a run that requested a specific city. Cleanup must
    remove the container (not just stop it), and the startup command must
    also force a recreate as a second, independent guarantee."""
    text = _workflow_text()

    assert "docker compose rm -f import-worker" in text
    assert "docker compose up -d --no-deps --force-recreate import-worker" in text

    rm_idx = text.index("docker compose rm -f import-worker")
    stop_idx = text.index("docker compose stop -t 30 import-worker")
    assert stop_idx < rm_idx


def test_city_slug_survives_workflow_input_to_compose_interpolation_new() -> None:
    """End-to-end trace for a real city_slug value ("almaty"): workflow
    input -> GHA env -> printf '%q' quoting -> SSH remote script default ->
    docker compose up inline env -> compose file interpolation. Executes
    the real printf '%q' quoting lines and the real docker compose up
    command line (with `docker` stubbed to just echo its argv) in an actual
    bash subshell, proving CITY_SLUG=almaty is never dropped, blanked, or
    replaced with a placeholder like "any" anywhere along the chain."""
    text = _workflow_text()

    quoting_lines = "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("REMOTE_") and "printf '%q'" in line
    )
    assert quoting_lines, "could not find the printf '%q' quoting lines in the workflow"

    up_line_start = text.index('IMPORT_WORKER_RUN_MODE="$RUN_MODE"')
    up_line_end = text.index("\n", up_line_start)
    up_line = text[up_line_start:up_line_end]

    script = f"""
set -euo pipefail
MAX_RUNTIME_SECONDS="300"
ADMIN_API_TOKEN="token"
WORKFLOW_NAME="CITY GO · OPS · Run Import Worker Safely"
WORKFLOW_RUN_ID="1"
WORKFLOW_RUN_URL="https://example.invalid/run/1"
RUN_MODE="safe_one_job"
CITY_SLUG="almaty"

{quoting_lines}

# Simulate what the remote script receives: re-parse the quoted assignment
# list exactly like the remote shell does, then apply the remote script's
# own ${{VAR:-default}} defaulting.
eval "RUN_MODE=$REMOTE_RUN_MODE CITY_SLUG=$REMOTE_CITY_SLUG"
RUN_MODE="${{RUN_MODE:-safe_one_job}}"
CITY_SLUG="${{CITY_SLUG:-}}"

docker() {{ echo "docker_argv:$*"; echo "seen_city_slug:[${{IMPORT_WORKER_CITY_SLUG:-}}]"; }}
timeout() {{ shift; "$@"; }}

{up_line}
"""
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"
    assert "docker_argv:compose up -d --no-deps --force-recreate import-worker" in result.stdout
    assert "seen_city_slug:[almaty]" in result.stdout
    assert "seen_city_slug:[]" not in result.stdout
    assert "seen_city_slug:[any]" not in result.stdout


def test_final_diagnostics_are_captured_before_cleanup_removes_container_new() -> None:
    """Regression: cleanup() runs `docker compose rm -f import-worker`,
    which deletes the container. If diagnostics (logs, exit code, OOM
    state) are read after cleanup, `docker inspect`/`docker compose logs`
    on an already-removed container return nothing — WORKER_EXIT_CODE and
    WORKER_OOM silently become "unknown" and the real logs are lost. All
    of this must be captured strictly before the `cleanup` call, not
    after."""
    text = _workflow_text()
    monitor_loop_start = text.index('section "monitor loop"')
    diagnostics_idx = text.index('section "final diagnostics', monitor_loop_start)
    logs_idx = text.index("docker compose logs --tail=250 import-worker", diagnostics_idx)
    exit_code_idx = text.index("WORKER_EXIT_CODE=$(docker inspect", diagnostics_idx)
    oom_idx = text.index("WORKER_OOM=$(docker inspect", diagnostics_idx)
    cleanup_call_idx = text.index("\n          cleanup\n", diagnostics_idx)
    trap_clear_idx = text.index("trap - EXIT", cleanup_call_idx)

    assert monitor_loop_start < diagnostics_idx < logs_idx < cleanup_call_idx
    assert monitor_loop_start < diagnostics_idx < exit_code_idx < cleanup_call_idx
    assert monitor_loop_start < diagnostics_idx < oom_idx < cleanup_call_idx
    assert cleanup_call_idx < trap_clear_idx
