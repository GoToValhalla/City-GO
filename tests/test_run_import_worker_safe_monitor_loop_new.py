"""Regression tests for the run-import-worker-safe.yml monitor loop's
health-check consecutive-failure logic (CI run 29192806410 root cause:
a single transient DNS timeout on the public health check was misread as
a confirmed unhealthy backend and killed a healthy worker)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_FILE = ROOT / ".github" / "workflows" / "run-import-worker-safe.yml"


def _workflow_text() -> str:
    return WORKFLOW_FILE.read_text(encoding="utf-8")


def _extract_monitor_loop_script() -> str:
    data = yaml.safe_load(_workflow_text())
    steps = data["jobs"]["run-import-worker-safe"]["steps"]
    script = next(
        step["run"] for step in steps if step.get("name") == "Preflight, run, monitor, and always stop import-worker"
    )
    match = re.search(r"bash <<'REMOTE_EOF'.*?\n(.*?)\nREMOTE_EOF", script, re.S)
    assert match is not None, "REMOTE_EOF heredoc body not found"
    body = match.group(1)

    loop_start = body.index('section "monitor loop"')
    loop_end = body.index("\ncleanup\ntrap - EXIT", loop_start)
    return body[loop_start:loop_end]


def _run_monitor_loop(tmp_path: Path, *, health_sequence: list[str], max_runtime_seconds: int = 300) -> subprocess.CompletedProcess:
    """Run the extracted monitor loop with a scripted sequence of health HTTP
    codes. Each iteration of the loop (one `sleep 5`) consumes one entry from
    health_sequence; ready/worker-state/memory are held fixed at healthy
    values so only the health-check consecutive-failure path is exercised."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sequence_file = tmp_path / "health_sequence.txt"
    sequence_file.write_text("\n".join(health_sequence) + "\n", encoding="utf-8")
    index_file = tmp_path / "health_index.txt"
    index_file.write_text("0", encoding="utf-8")

    (bin_dir / "curl").write_text(
        f"""#!/usr/bin/env bash
if [[ "$*" == *"/api/ready"* ]]; then
  printf '200'
  exit 0
fi
INDEX=$(cat "{index_file}")
CODE=$(sed -n "$((INDEX + 1))p" "{sequence_file}")
if [ -z "$CODE" ]; then
  CODE=200
fi
echo $((INDEX + 1)) > "{index_file}"
printf '%s' "$CODE"
exit 0
""",
        encoding="utf-8",
    )
    (bin_dir / "docker").write_text(
        """#!/usr/bin/env bash
if [[ "$*" == *"inspect"* ]]; then
  echo "running"
  exit 0
fi
if [[ "$*" == *"MemPerc"* ]]; then
  echo "15%"
  exit 0
fi
if [[ "$*" == *"stats"* ]]; then
  echo "10MiB / 512MiB"
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    (bin_dir / "awk").write_text(
        """#!/usr/bin/env bash
echo 900
""",
        encoding="utf-8",
    )
    (bin_dir / "sleep").write_text(
        """#!/usr/bin/env bash
exit 0
""",
        encoding="utf-8",
    )
    for name in ("curl", "docker", "awk", "sleep"):
        (bin_dir / name).chmod(0o755)

    loop_script = _extract_monitor_loop_script()
    script_path = tmp_path / "monitor_loop.sh"
    script_path.write_text(
        f"""#!/usr/bin/env bash
set -uo pipefail
section() {{ echo; echo "=== $1 ==="; }}
WORKER_ID=fake-worker-id
RUNTIME_HOST_FLOOR_MB=256
RUNTIME_CGROUP_PERCENT=85
MAX_RUNTIME_SECONDS={max_runtime_seconds}
{loop_script}
echo "FINAL_STOP_REASON=${{STOP_REASON}}"
echo "FINAL_ELAPSED=${{ELAPSED}}"
""",
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
    return subprocess.run(["bash", str(script_path)], capture_output=True, text=True, env=env)


def test_single_transient_dns_timeout_does_not_stop_worker(tmp_path: Path) -> None:
    result = _run_monitor_loop(tmp_path, health_sequence=["200", "000", "200", "200", "200"], max_runtime_seconds=25)

    assert "FINAL_STOP_REASON=max_runtime_reached" in result.stdout
    assert "ERROR: public health degraded" not in result.stderr
    assert "health_fail_streak=1" in result.stdout
    assert "health_fail_streak=0" in result.stdout


def test_health_recovery_resets_failure_counter(tmp_path: Path) -> None:
    result = _run_monitor_loop(
        tmp_path,
        health_sequence=["200", "000", "000", "200", "000", "000", "200", "200"],
        max_runtime_seconds=40,
    )

    assert "FINAL_STOP_REASON=max_runtime_reached" in result.stdout
    assert "ERROR: public health degraded" not in result.stderr
    assert result.stdout.count("health_fail_streak=2") == 2


def test_repeated_consecutive_failures_stop_worker(tmp_path: Path) -> None:
    result = _run_monitor_loop(
        tmp_path,
        health_sequence=["200", "000", "000", "000", "200", "200"],
        max_runtime_seconds=100,
    )

    assert "FINAL_STOP_REASON=public_health_degraded" in result.stdout
    assert "ERROR: public health degraded for 3 consecutive checks; stopping worker." in result.stderr
    assert "FINAL_ELAPSED=20" in result.stdout


def test_real_non_200_responses_still_stop_worker_after_threshold(tmp_path: Path) -> None:
    result = _run_monitor_loop(
        tmp_path,
        health_sequence=["200", "500", "503", "500", "200"],
        max_runtime_seconds=100,
    )

    assert "FINAL_STOP_REASON=public_health_degraded" in result.stdout
    assert "ERROR: public health degraded for 3 consecutive checks; stopping worker." in result.stderr
