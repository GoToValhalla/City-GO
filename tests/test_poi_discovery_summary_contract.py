from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

SCRIPT_PATH = Path("scripts/run_poi_discovery_remote.sh")
REQUIRED_SUMMARY_KEYS = {"status", "city_slug", "limit", "apply", "cities", "total_created", "failed_cities", "errors"}


def _script_for_test(tmp_path: Path) -> Path:
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    content = content.replace("cd /srv/app", 'cd "${CITYGO_TEST_APP_ROOT:?}"')
    script = tmp_path / "run_poi_discovery_remote.sh"
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    return script


def _write_fake_docker(tmp_path: Path, body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker = bin_dir / "docker"
    docker.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    docker.chmod(0o755)
    return bin_dir


def _run_script(script: Path, tmp_path: Path, fake_docker_body: str, *, city_slug: str = "", limit: str = "7", apply: str = "false") -> subprocess.CompletedProcess[str]:
    app_root = tmp_path / "app"
    app_root.mkdir(exist_ok=True)
    bin_dir = _write_fake_docker(tmp_path, fake_docker_body)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CITYGO_TEST_APP_ROOT": str(app_root),
        "CITY_SLUG": city_slug,
        "LIMIT": limit,
        "APPLY_DISCOVERED": apply,
        "QUEUE_TIMEOUT_SECONDS": "2",
        "PER_CITY_TIMEOUT_SECONDS": "2",
    }
    return subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env, timeout=10)


def _summary(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    combined = completed.stdout + completed.stderr
    assert "summary JSON не найден" not in combined
    lines = [line for line in completed.stdout.splitlines() if line.startswith("POI_DISCOVERY_SUMMARY_JSON=")]
    assert len(lines) == 1, combined
    payload = json.loads(lines[0].split("=", 1)[1])
    assert REQUIRED_SUMMARY_KEYS <= set(payload)
    return payload


def test_poi_discovery_always_emits_summary_json_when_compose_is_missing(tmp_path: Path):
    script = _script_for_test(tmp_path)
    completed = _run_script(script, tmp_path, """
        #!/usr/bin/env bash
        exit 1
    """)

    payload = _summary(completed)
    assert completed.returncode == 127
    assert payload["status"] == "error"
    assert payload["limit"] == 7
    assert payload["apply"] is False
    assert payload["failed_cities"] == 1
    assert payload["errors"] == ["compose_not_available"]


def test_poi_discovery_always_emits_summary_json_when_backend_container_is_missing(tmp_path: Path):
    script = _script_for_test(tmp_path)
    completed = _run_script(script, tmp_path, """
        #!/usr/bin/env bash
        if [[ "$*" == "compose version" ]]; then exit 0; fi
        if [[ "$*" == "compose ps -q backend" ]]; then exit 0; fi
        echo "unexpected docker args: $*" >&2
        exit 1
    """)

    payload = _summary(completed)
    assert completed.returncode == 1
    assert payload["status"] == "error"
    assert payload["errors"] == ["backend_container_not_found"]


def test_poi_discovery_always_emits_summary_json_when_city_queue_load_fails(tmp_path: Path):
    script = _script_for_test(tmp_path)
    completed = _run_script(script, tmp_path, """
        #!/usr/bin/env bash
        if [[ "$*" == "compose version" ]]; then exit 0; fi
        if [[ "$*" == "compose ps -q backend" ]]; then echo backend-1; exit 0; fi
        if [[ "$1" == "inspect" ]]; then echo running; exit 0; fi
        if [[ "$1" == "compose" && "$2" == "exec" ]]; then echo "db unavailable" >&2; exit 3; fi
        echo "unexpected docker args: $*" >&2
        exit 1
    """)

    payload = _summary(completed)
    assert completed.returncode == 1
    assert payload["status"] == "error"
    assert payload["errors"] == ["city_queue_load_failed:3"]


def test_poi_discovery_always_emits_summary_json_when_city_command_fails(tmp_path: Path):
    script = _script_for_test(tmp_path)
    completed = _run_script(script, tmp_path, """
        #!/usr/bin/env bash
        if [[ "$*" == "compose version" ]]; then exit 0; fi
        if [[ "$*" == "compose ps -q backend" ]]; then echo backend-1; exit 0; fi
        if [[ "$1" == "inspect" ]]; then echo running; exit 0; fi
        if [[ "$1" == "compose" && "$2" == "exec" ]]; then echo "city failed" >&2; exit 4; fi
        echo "unexpected docker args: $*" >&2
        exit 1
    """, city_slug="almaty")

    payload = _summary(completed)
    assert completed.returncode == 1
    assert payload["status"] == "partial_failure"
    assert payload["city_slug"] == "almaty"
    assert payload["failed_cities"] == 1
    assert payload["errors"] == ["almaty: city_command_failed:4"]
    assert payload["cities"][0]["city_slug"] == "almaty"


def test_poi_discovery_always_emits_summary_json_when_city_summary_is_missing(tmp_path: Path):
    script = _script_for_test(tmp_path)
    completed = _run_script(script, tmp_path, """
        #!/usr/bin/env bash
        if [[ "$*" == "compose version" ]]; then exit 0; fi
        if [[ "$*" == "compose ps -q backend" ]]; then echo backend-1; exit 0; fi
        if [[ "$1" == "inspect" ]]; then echo running; exit 0; fi
        if [[ "$1" == "compose" && "$2" == "exec" ]]; then echo "plain output without structured summary"; exit 0; fi
        echo "unexpected docker args: $*" >&2
        exit 1
    """, city_slug="almaty")

    payload = _summary(completed)
    assert completed.returncode == 1
    assert payload["status"] == "partial_failure"
    assert payload["failed_cities"] == 1
    assert payload["errors"] == ["almaty: city_summary_missing"]
