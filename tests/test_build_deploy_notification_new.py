"""Regression tests for scripts/build_deploy_notification.py.

Root cause this fixes: the previous _read_log_summary picked the LAST
non-empty line of each artifact log file (sorted alphabetically), regardless
of whether that line was an actual error — a routine status line from a
file with no failure (e.g. ssh-keyscan.log's success message, alphabetically
before deploy-on-server.log) could push the real failing file's message out
of the top-5 window entirely, and even the right file's last line was often
just routine progress output ("=== Docker compose status ==="), not the
ERROR that explains what broke. The notification never named which deploy
stage failed either. These tests pin down the fixed behavior: only real
ERROR/Traceback/FAILED lines are surfaced, tagged with a human-readable
stage name derived from the log filename.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_deploy_notification import build_message

pytestmark = [pytest.mark.unit, pytest.mark.regression]


def test_success_message_has_no_error_section_new(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "111")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "7")
    monkeypatch.setenv("CITY_GO_DEPLOY_SHA", "abc1234def5678901234567890123456789abcd")
    monkeypatch.setenv("CITY_GO_DEPLOY_REF", "main")

    message = build_message(
        build_result="success",
        deploy_result="success",
        run_attempt="1",
        log_dir=tmp_path,
    )

    assert "✅ CITY GO · PRODUCTION DEPLOY" in message
    assert "прод обновлён" in message
    assert "Причина сбоя" not in message
    assert "abc1234" in message
    assert "https://github.com/GoToValhalla/City-GO/actions/runs/111" in message


def test_failure_surfaces_real_error_lines_not_last_lines_new(tmp_path: Path, monkeypatch) -> None:
    """Reproduces the exact incident: an alphabetically-earlier file with no
    real error (ssh-keyscan.log) must not push the real failure
    (deploy-on-server.log's ERROR line) out of the report, and the report
    must show the ERROR line, not deploy-on-server.log's last (routine)
    line."""
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "222")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "8")

    (tmp_path / "ssh-keyscan.log").write_text(
        "SSH host key preflight succeeded attempt=1\n", encoding="utf-8"
    )
    (tmp_path / "deploy-on-server.log").write_text(
        "=== docker load (bounded) ===\n"
        "=== docker compose up (bounded) ===\n"
        "ERROR: docker compose up timed out or failed (exit code 1)\n"
        "=== docker compose ps -a ===\n"
        "app-migrate-1   Exit 1\n",
        encoding="utf-8",
    )

    message = build_message(
        build_result="success",
        deploy_result="failure",
        run_attempt="1",
        log_dir=tmp_path,
    )

    assert "Причина сбоя" in message
    assert "ERROR: docker compose up timed out or failed (exit code 1)" in message
    # The routine last line of deploy-on-server.log must not be the thing shown.
    assert "app-migrate-1   Exit 1" not in message
    # ssh-keyscan.log contributed no error section since it has no ERROR line.
    assert "SSH host key preflight succeeded" not in message


def test_failure_names_the_failed_stage_new(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "333")

    (tmp_path / "verify-build-json.log").write_text(
        "--- attempt 1/10 ---\n"
        "HTTP status: 200 (curl exit 0)\n"
        "ERROR: build.json did not confirm the expected SHA after 10 attempts (~30s).\n",
        encoding="utf-8",
    )

    message = build_message(
        build_result="success",
        deploy_result="failure",
        run_attempt="1",
        log_dir=tmp_path,
    )

    assert "[Проверка build.json]" in message
    assert "ERROR: build.json did not confirm the expected SHA" in message


def test_failure_with_no_error_lines_says_so_explicitly_new(tmp_path: Path, monkeypatch) -> None:
    """If every log file exists but none contains a real error line (e.g. a
    step failed via a non-zero exit with no ERROR: text logged), the
    notification must say so rather than silently show nothing or fall back
    to misleading routine output."""
    monkeypatch.setenv("GITHUB_RUN_ID", "444")

    (tmp_path / "deploy-on-server.log").write_text(
        "=== docker load (bounded) ===\nOK\n", encoding="utf-8"
    )

    message = build_message(
        build_result="success",
        deploy_result="failure",
        run_attempt="1",
        log_dir=tmp_path,
    )

    assert "Реальные ERROR-строки не найдены" in message


def test_missing_log_dir_does_not_crash_new(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "555")
    missing_dir = tmp_path / "does-not-exist"

    message = build_message(
        build_result="failure",
        deploy_result="failure",
        run_attempt="2",
        log_dir=missing_dir,
    )

    assert "❌ CITY GO · PRODUCTION DEPLOY" in message
    assert "Реальные ERROR-строки не найдены" in message


def test_multiple_failed_stages_each_reported_new(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_RUN_ID", "666")

    (tmp_path / "deploy-on-server.log").write_text(
        "ERROR: docker load timed out or failed (exit code 124)\n", encoding="utf-8"
    )
    (tmp_path / "verify-build-json.log").write_text(
        "ERROR: build.json did not confirm the expected SHA after 10 attempts (~30s).\n",
        encoding="utf-8",
    )

    message = build_message(
        build_result="success",
        deploy_result="failure",
        run_attempt="1",
        log_dir=tmp_path,
    )

    assert "[Деплой на сервер (docker load/compose up)]" in message
    assert "[Проверка build.json]" in message
    assert "ERROR: docker load timed out" in message
    assert "ERROR: build.json did not confirm" in message
