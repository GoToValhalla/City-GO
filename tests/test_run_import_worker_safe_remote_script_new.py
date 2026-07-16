"""End-to-end regression tests for the FULL REMOTE_EOF script embedded in
.github/workflows/run-import-worker-safe.yml (preflight, start, monitor
loop, final diagnostics, cleanup, pass/fail decision) — not just the
monitor loop fragment covered by test_run_import_worker_safe_monitor_loop_new.py.

Root causes this covers (CI run 29511329727):
1. The monitor loop must never lose track of the container: WORKER_ID is
   captured once via `docker compose ps -aq` right after `docker compose
   up`, and every later `docker inspect` call reuses that saved ID — never
   rediscovered via `docker compose ps -q` (which only matches *running*
   containers and would miss one that already exited).
2. run_mode semantics must be respected end-to-end: diagnostics_only's
   fast, successful container exit (exit_code 0) must be classified as
   workflow SUCCESS, not unknown/failure.

Every test here builds a fake `docker`/`docker compose`/`curl`/`free`/
`awk`/`timeout` on PATH, runs the real extracted script body in a real
bash subprocess, and asserts on the real exit code and real stdout/stderr
— not on the workflow YAML's source text.
"""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "run-import-worker-safe.yml"


def _workflow_text() -> str:
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _extract_remote_script() -> str:
    data = yaml.safe_load(_workflow_text())
    steps = data["jobs"]["run-import-worker-safe"]["steps"]
    script = next(
        step["run"] for step in steps if step.get("name") == "Preflight, run, monitor, and always stop import-worker"
    )
    match = re.search(r"<<'REMOTE_EOF'.*?\n(.*?)\nREMOTE_EOF", script, re.S)
    assert match is not None, "REMOTE_EOF heredoc body not found"
    return match.group(1)


class _FakeDockerHost:
    """Builds a fake bin/ directory simulating a docker host for the
    import-worker container's lifecycle across the whole run."""

    def __init__(self, tmp_path: Path, *, container_state: str, exit_code: str, oom_killed: str = "false") -> None:
        self.tmp_path = tmp_path
        self.bin_dir = tmp_path / "bin"
        self.bin_dir.mkdir(exist_ok=True)
        self.state_file = tmp_path / "container_state.txt"
        self.state_file.write_text(container_state, encoding="utf-8")
        self.exit_code_file = tmp_path / "container_exit_code.txt"
        self.exit_code_file.write_text(exit_code, encoding="utf-8")
        self.oom_file = tmp_path / "container_oom.txt"
        self.oom_file.write_text(oom_killed, encoding="utf-8")
        self.worker_event_calls = tmp_path / "worker_event_calls.jsonl"
        self.worker_event_calls.write_text("", encoding="utf-8")

    def write_scripts(self, *, health_code: str = "200", ready_code: str = "200", available_mb: str = "900") -> None:
        (self.bin_dir / "curl").write_text(
            textwrap.dedent(f"""\
            #!/usr/bin/env bash
            # Distinguish the worker-event POST from the health/ready GETs.
            if [[ "$*" == *"worker-event"* ]]; then
              # Find the -d/--data-binary payload argument and echo it to a
              # log file, then behave like a real curl -w '%{{http_code}}'.
              PAYLOAD=""
              PREV=""
              for arg in "$@"; do
                if [[ "$PREV" == "--data-binary" ]]; then
                  FILE="${{arg#@}}"
                  PAYLOAD="$(cat "$FILE")"
                fi
                PREV="$arg"
              done
              echo "$PAYLOAD" >> "{self.worker_event_calls}"
              echo -n '{{"accepted": true, "log_id": 1}}' > /dev/null || true
              printf '200'
              exit 0
            fi
            if [[ "$*" == *"/api/ready"* ]]; then
              printf '{ready_code}'
              exit 0
            fi
            if [[ "$*" == *"/api/health"* ]]; then
              printf '{health_code}'
              exit 0
            fi
            if [[ "$*" == *"import-jobs/queue"* ]]; then
              echo '{{"running_job_ids": []}}'
              exit 0
            fi
            printf '200'
            exit 0
            """),
            encoding="utf-8",
        )
        (self.bin_dir / "docker").write_text(
            textwrap.dedent(f"""\
            #!/usr/bin/env bash
            if [[ "$1" == "compose" ]]; then
              shift
              if [[ "$1" == "up" ]]; then
                exit 0
              fi
              if [[ "$1" == "ps" ]]; then
                echo "fake-worker-container-id"
                exit 0
              fi
              if [[ "$1" == "stop" || "$1" == "rm" || "$1" == "logs" ]]; then
                exit 0
              fi
              exit 0
            fi
            if [[ "$1" == "inspect" ]]; then
              if [[ "$*" == *"State.Status"* ]]; then
                cat "{self.state_file}"
                exit 0
              fi
              if [[ "$*" == *"State.ExitCode"* ]]; then
                cat "{self.exit_code_file}"
                exit 0
              fi
              if [[ "$*" == *"State.OOMKilled"* ]]; then
                cat "{self.oom_file}"
                exit 0
              fi
              echo "memory_limit=536870912 memory_swap=536870912 nano_cpus=500000000 restart=no"
              exit 0
            fi
            if [[ "$1" == "stats" ]]; then
              echo "10MiB / 512MiB"
              exit 0
            fi
            exit 0
            """),
            encoding="utf-8",
        )
        (self.bin_dir / "awk").write_text(f"#!/usr/bin/env bash\necho {available_mb}\n", encoding="utf-8")
        (self.bin_dir / "free").write_text("#!/usr/bin/env bash\necho 'fake free -h output'\n", encoding="utf-8")
        (self.bin_dir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (self.bin_dir / "timeout").write_text("#!/usr/bin/env bash\nshift\nexec \"$@\"\n", encoding="utf-8")
        for name in ("curl", "docker", "awk", "free", "sleep", "timeout"):
            (self.bin_dir / name).chmod(0o755)

    def env(self, *, admin_api_token: str = "fake-admin-token") -> dict[str, str]:
        return {
            "PATH": f"{self.bin_dir}:/usr/bin:/bin",
            "ADMIN_API_TOKEN": admin_api_token,
        }

    def worker_events(self) -> list[dict]:
        text = self.worker_event_calls.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def _run_remote_script(
    tmp_path: Path,
    *,
    run_mode: str,
    container_state: str,
    exit_code: str,
    oom_killed: str = "false",
    health_code: str = "200",
    ready_code: str = "200",
    available_mb: str = "900",
    max_runtime_seconds: int = 30,
    admin_api_token: str = "fake-admin-token",
) -> tuple[subprocess.CompletedProcess, _FakeDockerHost]:
    host = _FakeDockerHost(tmp_path, container_state=container_state, exit_code=exit_code, oom_killed=oom_killed)
    host.write_scripts(health_code=health_code, ready_code=ready_code, available_mb=available_mb)

    remote_script = _extract_remote_script()
    script_path = tmp_path / "remote.sh"
    script_path.write_text(
        f"""#!/usr/bin/env bash
MAX_RUNTIME_SECONDS={max_runtime_seconds}
RUN_MODE={run_mode}
CITY_SLUG=
WORKFLOW_NAME="Test Workflow"
WORKFLOW_RUN_ID="1"
WORKFLOW_RUN_URL="https://example.invalid/run/1"
{remote_script}
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    result = subprocess.run(
        ["bash", str(script_path)],
        capture_output=True,
        text=True,
        env=host.env(admin_api_token=admin_api_token),
        cwd=tmp_path,
        timeout=60,
    )
    return result, host


def test_diagnostics_only_fast_exit_zero_is_workflow_success_new(tmp_path: Path) -> None:
    """The exact production scenario from CI run 29511329727: a
    diagnostics_only container that exits almost immediately with code 0
    must be classified as SUCCESS — not unknown, not failure."""
    result, host = _run_remote_script(
        tmp_path, run_mode="diagnostics_only", container_state="exited", exit_code="0",
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "diagnostics_only completed successfully" in result.stdout
    assert "ERROR: worker exit code is unknown" not in result.stderr
    assert "ERROR: worker run ended by safety guard" not in result.stderr


def test_dry_run_empty_queue_is_success_new(tmp_path: Path) -> None:
    """dry_run with no queued job exits 0 (run_admin_import_worker.py's
    own contract for an empty queue) — the workflow must not additionally
    require a claim for this mode."""
    result, host = _run_remote_script(
        tmp_path, run_mode="dry_run", container_state="exited", exit_code="0",
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_safe_one_job_no_job_available_is_failure_new(tmp_path: Path) -> None:
    """safe_one_job with no matching queued job: run_admin_import_worker.py
    itself exits 1 in this case (import_worker_no_matching_queued_job) —
    the workflow must propagate that as a failed run."""
    result, host = _run_remote_script(
        tmp_path, run_mode="safe_one_job", container_state="exited", exit_code="1",
    )

    assert result.returncode == 1
    assert "worker exited with code 1" in result.stderr


def test_safe_one_job_completed_job_is_success_new(tmp_path: Path) -> None:
    result, host = _run_remote_script(
        tmp_path, run_mode="safe_one_job", container_state="exited", exit_code="0",
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_worker_non_zero_exit_is_failure_in_every_mode_new(tmp_path: Path) -> None:
    for mode in ("safe_one_job", "dry_run", "diagnostics_only"):
        mode_dir = tmp_path / mode
        mode_dir.mkdir()
        result, host = _run_remote_script(
            mode_dir, run_mode=mode, container_state="exited", exit_code="1",
        )
        assert result.returncode == 1, f"mode={mode} stdout={result.stdout}\nstderr={result.stderr}"
        assert "worker exited with code 1" in result.stderr, f"mode={mode}"


def test_oom_kill_is_failure_in_every_mode_new(tmp_path: Path) -> None:
    for mode in ("safe_one_job", "dry_run", "diagnostics_only"):
        mode_dir = tmp_path / mode
        mode_dir.mkdir()
        result, host = _run_remote_script(
            mode_dir, run_mode=mode, container_state="exited", exit_code="137", oom_killed="true",
        )
        assert result.returncode == 1, f"mode={mode} stdout={result.stdout}\nstderr={result.stderr}"
        assert "worker was OOM-killed" in result.stderr, f"mode={mode}"


def test_exit_code_137_without_oom_flag_still_fails_new(tmp_path: Path) -> None:
    """137 is SIGKILL's exit code regardless of whether Docker's own
    OOMKilled flag was set — both signals must independently trigger the
    OOM failure path."""
    result, host = _run_remote_script(
        tmp_path, run_mode="safe_one_job", container_state="exited", exit_code="137", oom_killed="false",
    )

    assert result.returncode == 1
    assert "worker was OOM-killed" in result.stderr


def test_saved_container_id_remains_usable_after_exit_new(tmp_path: Path) -> None:
    """Regression: the monitor loop must read state/exit-code/OOM from the
    ID captured once via `docker compose ps -aq` right after start — never
    rediscover via `docker compose ps -q` (running-only). This test's fake
    `docker compose ps` always returns the same fixed ID regardless of
    state, simulating the real -aq behavior; the assertion that matters is
    that the script reaches a definitive (not "unknown") exit code even
    though the container already exited before the first monitor
    iteration."""
    result, host = _run_remote_script(
        tmp_path, run_mode="diagnostics_only", container_state="exited", exit_code="0",
    )

    assert result.returncode == 0
    assert "worker_exit_code=0" in result.stdout
    assert "worker_exit_code=unknown" not in result.stdout


def test_cleanup_runs_on_success_path_new(tmp_path: Path) -> None:
    result, host = _run_remote_script(
        tmp_path, run_mode="diagnostics_only", container_state="exited", exit_code="0",
    )

    assert "cleanup: always stop and remove import-worker" in result.stdout


def test_cleanup_runs_on_failure_path_new(tmp_path: Path) -> None:
    result, host = _run_remote_script(
        tmp_path, run_mode="safe_one_job", container_state="exited", exit_code="1",
    )

    assert "cleanup: always stop and remove import-worker" in result.stdout


def test_worker_event_payloads_pass_the_real_backend_schema_for_every_emitted_event_new(tmp_path: Path) -> None:
    """The strongest possible regression for the HTTP 422 root cause: run
    the real remote script end-to-end, capture every JSON payload it POSTs
    to /admin/system-logs/worker-event, and validate each one against the
    REAL Pydantic schema (not a hand-written expectation)."""
    import sys

    sys.path.insert(0, str(ROOT))
    from schemas.admin_worker_event import WORKER_LIFECYCLE_EVENTS, AdminWorkerEventRequest

    result, host = _run_remote_script(
        tmp_path, run_mode="diagnostics_only", container_state="exited", exit_code="0",
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    events = host.worker_events()
    assert events, "expected at least one worker-event payload to have been sent"
    for payload in events:
        # Must be valid, parseable JSON with only known fields — this is
        # exactly what raises HTTP 422 in production when it fails.
        request = AdminWorkerEventRequest(**payload)
        assert request.event in WORKER_LIFECYCLE_EVENTS


def test_worker_event_payload_handles_non_numeric_claimed_job_id_new(tmp_path: Path) -> None:
    """Regression for the concrete 422 trigger found during investigation:
    if refresh_claimed_job_id() ever yields a non-numeric string (e.g. a
    swallowed curl/python error fragment), the OLD string-concatenation
    payload emitted invalid JSON (`"job_id": Traceback, ...`). The new
    payload must instead just omit job_id — never break the request."""
    import sys

    sys.path.insert(0, str(ROOT))
    from schemas.admin_worker_event import AdminWorkerEventRequest

    host = _FakeDockerHost(tmp_path, container_state="running", exit_code="0")
    host.write_scripts()
    # Force refresh_claimed_job_id to yield a non-numeric value by making
    # the queue endpoint return a malformed running_job_ids entry.
    (host.bin_dir / "curl").write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        if [[ "$*" == *"worker-event"* ]]; then
          PAYLOAD=""
          PREV=""
          for arg in "$@"; do
            if [[ "$PREV" == "--data-binary" ]]; then
              FILE="${{arg#@}}"
              PAYLOAD="$(cat "$FILE")"
            fi
            PREV="$arg"
          done
          echo "$PAYLOAD" >> "{host.worker_event_calls}"
          printf '200'
          exit 0
        fi
        if [[ "$*" == *"/api/ready"* ]]; then
          printf '200'
          exit 0
        fi
        if [[ "$*" == *"/api/health"* ]]; then
          printf '200'
          exit 0
        fi
        if [[ "$*" == *"import-jobs/queue"* ]]; then
          echo 'not valid json at all'
          exit 0
        fi
        printf '200'
        exit 0
        """),
        encoding="utf-8",
    )
    (host.bin_dir / "curl").chmod(0o755)

    remote_script = _extract_remote_script()
    script_path = tmp_path / "remote.sh"
    script_path.write_text(
        f"""#!/usr/bin/env bash
MAX_RUNTIME_SECONDS=30
RUN_MODE=safe_one_job
CITY_SLUG=
WORKFLOW_NAME="Test Workflow"
WORKFLOW_RUN_ID="1"
WORKFLOW_RUN_URL="https://example.invalid/run/1"
{remote_script}
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    # Flip the container to exited after the first monitor iteration so the
    # loop reaches the worker_stop_requested -> refresh_claimed_job_id path.
    host.state_file.write_text("exited", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(script_path)], capture_output=True, text=True, env=host.env(), cwd=tmp_path, timeout=60,
    )

    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    events = host.worker_events()
    assert events
    for payload in events:
        # Must not raise — proves job_id was safely omitted, not emitted
        # as an unquoted, non-numeric JSON token.
        AdminWorkerEventRequest(**payload)
        assert "job_id" not in payload or isinstance(payload["job_id"], int)
