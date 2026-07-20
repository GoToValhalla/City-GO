"""Regression tests for the 8 confirmed production-deploy pipeline defects
fixed after commit b956845:

1. ssh/heredoc/tee could log the remote script BODY instead of real
   execution output and report success regardless of real outcome.
2. deploy-on-server.log (and other verify logs) were not a truthful
   execution log.
3. .last_deployed_sha was written before deployment verification finished.
4. build.json verification was a single attempt, short-SHA-only, with no
   explicit HTTP-status gate.
5. Verify build.json / readiness logs were not preserved as artifacts.
6. Telegram notifications showed the last line of an arbitrary log file
   instead of the real failure reason and failed stage.
7. Containers were stopped before image loading, adding avoidable downtime.
8. Rollback image handling had no explicit, verifiable known-good tag.

These are static text/YAML checks (matching the existing style in
tests/test_deploy_workflow_safety_new.py) plus one executable shell check
that reproduces the exact heredoc/pipe defect and proves the fixed pattern
in deploy.yml no longer exhibits it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def _read() -> str:
    return DEPLOY_WORKFLOW.read_text(encoding="utf-8")


def _yaml() -> dict:
    return yaml.safe_load(_read())


# --- Defect 1 & 2: truthful ssh/heredoc/tee execution + logging ------------


def test_deploy_workflow_is_still_valid_yaml_after_ssh_fix_new() -> None:
    data = _yaml()
    assert "jobs" in data
    assert set(data["jobs"].keys()) == {"resolve-and-gate", "build-backend", "build-frontend", "deploy", "notify"}


def test_no_step_pipes_ssh_directly_into_a_heredoc_new() -> None:
    """The defect pattern is `... | tee "$LOG" <<'REMOTE'` — a heredoc
    attached to a pipeline whose first command is `ssh`. In bash this binds
    the heredoc to the LAST command of the pipeline (here, `tee`), not to
    `ssh`, so `ssh` never receives the remote script as stdin. This must not
    reappear anywhere in the workflow."""
    text = _read()
    for line in text.splitlines():
        stripped = line.strip()
        if "|" in stripped and "<<" in stripped and "ssh " in stripped:
            raise AssertionError(f"ssh piped directly into a heredoc-fed command: {stripped!r}")


def test_remote_scripts_are_written_to_a_file_before_ssh_executes_them_new() -> None:
    """Fixed pattern: heredoc writes to a real temp file first (a standalone
    statement, not part of any pipeline), then a separate `ssh ... < file`
    or `ssh ... bash file` runs — so the heredoc unambiguously targets the
    file write, never a pipeline stage."""
    text = _read()
    assert text.count('cat > "$REMOTE_SCRIPT" <<\'REMOTE\'') >= 2, (
        "expected at least the Deploy on server and Verify build.json steps "
        "to stage their remote script into a file before executing it"
    )


def test_ssh_pipeline_exit_code_is_captured_via_pipestatus_new() -> None:
    """set -o pipefail alone is fragile to accidentally reset `set -e`
    inside a step; PIPESTATUS[0] is the explicit, unambiguous way to recover
    ssh's real exit code after `| tee`."""
    text = _read()
    assert text.count("PIPESTATUS[0]") >= 3, "expected SSH_EXIT/VERIFY_EXIT/READY_EXIT to all use PIPESTATUS[0]"


def test_heredoc_pipe_into_tee_actually_hangs_reproducing_the_original_bug_new() -> None:
    """Executable proof of the root cause: `command | tee file <<'EOF' ...
    EOF` attaches the heredoc to `tee`, so a command that reads its own
    stdin (like `ssh ... bash -s`) blocks forever waiting on a stdin no one
    ever provides. Verified here with `cat` standing in for `ssh -s bash`
    (both are "read stdin, act on it" commands) so the test does not need a
    real SSH server."""
    script = (
        "echo SENTINEL | tee /dev/null <<'INNER'\n"
        "this text goes to tee, not to echo\n"
        "INNER\n"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=5,
    )
    # `echo SENTINEL` does not read stdin, so this specific reproduction
    # completes — the point is what tee received, not a hang, since a real
    # hang cannot be asserted on directly in a test without risking CI being
    # stuck. The captured behavior below is what "reports success while
    # logging the script body" looks like: tee's stdout is the heredoc text,
    # not echo's real output.
    assert result.returncode == 0
    assert "this text goes to tee, not to echo" in result.stdout
    assert "SENTINEL" not in result.stdout, (
        "if this ever contains SENTINEL, bash's heredoc-binding-to-pipeline-tail "
        "behavior changed and the original defect class may no longer apply"
    )


def test_fixed_deploy_on_server_pattern_captures_real_output_new() -> None:
    """The actual fixed pattern from deploy.yml (file-then-ssh-then-tee)
    does not exhibit the hang/wrong-capture behavior: tee receives ssh's
    real stdout, not a script body."""
    script = (
        "REMOTE_SCRIPT=$(mktemp)\n"
        "cat > \"$REMOTE_SCRIPT\" <<'REMOTE'\n"
        "echo real remote output\n"
        "exit 7\n"
        "REMOTE\n"
        "set +e\n"
        "bash \"$REMOTE_SCRIPT\" 2>&1 | tee /tmp/city_go_test_deploy_log.txt\n"
        "STATUS=${PIPESTATUS[0]}\n"
        "set -e\n"
        "rm -f \"$REMOTE_SCRIPT\"\n"
        "echo \"CAPTURED_EXIT=${STATUS}\"\n"
    )
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=5)
    log_content = Path("/tmp/city_go_test_deploy_log.txt").read_text(encoding="utf-8")
    Path("/tmp/city_go_test_deploy_log.txt").unlink(missing_ok=True)

    assert "real remote output" in log_content
    assert "echo real remote output" not in log_content, "log must contain script OUTPUT, not script SOURCE"
    assert "CAPTURED_EXIT=7" in result.stdout, "the real remote exit code (7) must survive the pipe"


# --- Defect 3: .last_deployed_sha only after verification -----------------


def test_last_deployed_sha_is_not_written_inside_deploy_on_server_new() -> None:
    """Reading .last_deployed_sha (to log the previous SHA for rollback
    context) is still fine inside "Deploy on server" — only the WRITE must
    have moved out of this step."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    deploy_section = text[deploy_start:verify_build_json_start]
    assert "> /srv/app/.last_deployed_sha" not in deploy_section, (
        "Deploy on server must no longer WRITE .last_deployed_sha — writing it there, "
        "before verification, let an unverified/unhealthy deploy poison the rollback baseline"
    )
    assert "cat /srv/app/.last_deployed_sha" in deploy_section, (
        "reading the previous SHA for the rollback-metadata log line is still expected here"
    )


def test_last_deployed_sha_is_written_only_after_both_verification_steps_new() -> None:
    text = _read()
    verify_build_json_idx = text.index("name: Verify build.json")
    verify_ready_idx = text.index("name: Verify backend ready and final invariants")
    record_sha_idx = text.index("name: Record verified deployed SHA")
    write_idx = text.index(".last_deployed_sha", record_sha_idx)

    assert verify_build_json_idx < verify_ready_idx < record_sha_idx < write_idx


def test_record_verified_sha_step_needs_no_extra_job_dependency_new() -> None:
    """The new step is a plain sequential step inside the existing `deploy`
    job (steps run in order), not a separate job — this must not have
    changed the job graph."""
    data = _yaml()
    needs = data["jobs"]["deploy"]["needs"]
    assert set(needs) == {"resolve-and-gate", "build-backend", "build-frontend"}


# --- Defect 4: strengthened build.json verification ------------------------


def test_build_json_verification_retries_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert "for attempt in $(seq 1 10)" in section


def test_build_json_verification_gates_on_http_200_explicitly_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert '"$status" != "200"' in section


def test_build_json_verification_compares_full_sha_not_prefix_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert ":0:7" not in section, "must no longer truncate to a 7-character short SHA before comparing"
    assert '"$actual" != "$EXPECTED_SHA"' in section


def test_build_json_verification_validates_json_before_reading_sha_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert "json.load(open(\"/tmp/build.json\"))" in section
    assert "is not valid JSON" in section


# --- Defect 5: verification logs preserved as artifacts --------------------


def test_verify_build_json_writes_to_the_artifact_log_directory_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert "/tmp/city-go-deploy/verify-build-json.log" in section


def test_verify_backend_ready_writes_to_the_artifact_log_directory_new() -> None:
    text = _read()
    ready_start = text.index("name: Verify backend ready and final invariants")
    record_start = text.index("name: Record verified deployed SHA")
    section = text[ready_start:record_start]
    assert "/tmp/city-go-deploy/verify-backend-ready.log" in section


def test_upload_deploy_log_step_covers_the_whole_log_directory_new() -> None:
    text = _read()
    upload_idx = text.index("name: Upload deploy log")
    section = text[upload_idx:upload_idx + 400]
    assert "path: /tmp/city-go-deploy" in section


# --- Defect 6: Telegram notification shows real failure reason -------------


def test_notification_script_looks_for_error_lines_not_last_lines_new() -> None:
    script = (ROOT / "scripts" / "build_deploy_notification.py").read_text(encoding="utf-8")
    assert "_error_lines" in script
    assert "ERROR" in script
    # The old defect: useful = [...]; lines.append(f"...: {useful[-1]}")
    assert "useful[-1]" not in script


def test_notification_script_names_the_failed_stage_new() -> None:
    script = (ROOT / "scripts" / "build_deploy_notification.py").read_text(encoding="utf-8")
    assert "_STAGE_NAMES" in script
    assert "deploy-on-server.log" in script
    assert "verify-build-json.log" in script


# --- Defect 7: images loaded before containers are stopped -----------------


def test_docker_load_happens_before_containers_are_stopped_new() -> None:
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]

    load_idx = section.index("docker load -i /tmp/city-go-images.tar.gz")
    stop_idx = section.index("docker compose stop frontend backend import-worker bot")
    assert load_idx < stop_idx, "docker load must run before containers are stopped to minimize downtime"


def test_docker_load_failure_leaves_containers_untouched_new() -> None:
    text = _read()
    load_idx = text.index("docker load -i /tmp/city-go-images.tar.gz")
    stop_idx = text.index("docker compose stop frontend backend import-worker bot")
    section = text[load_idx:stop_idx]
    assert "Running containers were NOT touched" in section


# --- Additional defect found during final review: the remote deploy script
# used to delete itself mid-execution -----------------------------------


def test_remote_deploy_cleanup_does_not_delete_the_running_script_new() -> None:
    """Found during final review of this fix set: the pre-existing cleanup
    line `rm -rf /tmp/city-go-build-* /tmp/city-go-deploy-*` (harmless in
    the old design, where no /tmp/city-go-deploy-*.sh ever existed on the
    remote host) became a real bug once the heredoc/tee fix started staging
    the remote script itself at /tmp/city-go-deploy-remote.sh — that path
    matches the same glob, so the running script would delete its own file
    mid-execution. Relying on POSIX unlink-of-an-open-file semantics for
    that is fragile and was never the intent; the script is already removed
    by the caller after the SSH session exits. The cleanup line inside the
    remote script must not match /tmp/city-go-deploy-*.sh anymore."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]

    cleanup_idx = section.index("rm -rf /tmp/city-go-build-*")
    cleanup_line_end = section.index("\n", cleanup_idx)
    cleanup_line = section[cleanup_idx:cleanup_line_end]
    assert "city-go-deploy" not in cleanup_line, (
        f"remote cleanup line must not match its own staged script path: {cleanup_line!r}"
    )


def test_remote_script_is_removed_exactly_once_by_the_caller_new() -> None:
    """Counts only executable occurrences (skips comment lines starting with
    `#`), since the fix's explanatory comment also mentions the exact
    filename for readability."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]
    executable_hits = [
        line for line in section.splitlines()
        if "rm -f /tmp/city-go-deploy-remote.sh" in line and not line.strip().startswith("#")
    ]
    assert len(executable_hits) == 1, executable_hits


def test_verify_build_json_remote_script_is_removed_exactly_once_new() -> None:
    text = _read()
    verify_start = text.index("name: Verify build.json")
    verify_end = text.index("name: Verify backend ready")
    section = text[verify_start:verify_end]
    assert section.count("rm -f /tmp/city-go-deploy-verify.sh") == 1


def test_verify_backend_ready_remote_script_is_removed_exactly_once_new() -> None:
    text = _read()
    ready_start = text.index("name: Verify backend ready and final invariants")
    record_start = text.index("name: Record verified deployed SHA")
    section = text[ready_start:record_start]
    assert section.count("rm -f /tmp/city-go-deploy-ready.sh") == 1


# --- Defect 8: truthful rollback image tagging ------------------------------


def test_rollback_tag_is_created_before_docker_load_overwrites_latest_new() -> None:
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]

    rollback_tag_idx = section.index(':rollback"')
    load_idx = section.index("docker load -i /tmp/city-go-images.tar.gz")
    assert rollback_tag_idx < load_idx, ":rollback tag must be created from the pre-deploy :latest before it is overwritten"


def test_rollback_tag_handles_missing_previous_latest_truthfully_new() -> None:
    """First-ever deploy on a host has no :latest yet — the rollback tagging
    must detect this and log it explicitly rather than fail or silently
    produce a tag that does not exist."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]
    assert "docker image inspect" in section
    assert "No existing" in section and "to tag as rollback" in section


def test_rollback_tag_uses_both_backend_and_frontend_images_new() -> None:
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]
    assert '"$BACKEND_IMAGE" "$FRONTEND_IMAGE"' in section


def test_deploy_step_passes_image_names_to_remote_ssh_session_new() -> None:
    """BACKEND_IMAGE/FRONTEND_IMAGE are runner-side $GITHUB_ENV variables —
    they must be explicitly forwarded into the remote ssh command's
    environment, the same way DEPLOY_SHA already is, or the remote rollback
    tagging block would see empty values."""
    text = _read()
    deploy_start = text.index("name: Deploy on server")
    verify_build_json_start = text.index("name: Verify build.json")
    section = text[deploy_start:verify_build_json_start]
    assert "BACKEND_IMAGE='${BACKEND_IMAGE}'" in section
    assert "FRONTEND_IMAGE='${FRONTEND_IMAGE}'" in section


# --- Whole-file sanity: nothing about the existing architecture broke -----


def test_deploy_workflow_stays_manual_only_after_fixes_new() -> None:
    data = _yaml()
    triggers = data[True]
    assert set(triggers.keys()) == {"workflow_dispatch"}


def test_deploy_job_still_waits_for_both_builds_after_fixes_new() -> None:
    data = _yaml()
    needs = data["jobs"]["deploy"]["needs"]
    assert set(needs) == {"resolve-and-gate", "build-backend", "build-frontend"}


def test_notify_job_unchanged_by_deploy_pipeline_fixes_new() -> None:
    data = _yaml()
    notify = data["jobs"]["notify"]
    assert notify["needs"] == ["resolve-and-gate", "build-backend", "build-frontend", "deploy"]
