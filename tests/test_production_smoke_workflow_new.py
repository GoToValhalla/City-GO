"""Static safety checks for .github/workflows/production-smoke.yml — the
smoke result and Telegram delivery result must be independent: Telegram
failure must never turn a passing smoke run red, and smoke failure must
still fail the workflow regardless of Telegram outcome."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SMOKE_WORKFLOW = ROOT / ".github" / "workflows" / "production-smoke.yml"


def _read() -> str:
    return SMOKE_WORKFLOW.read_text(encoding="utf-8")


def _yaml() -> dict:
    return yaml.safe_load(_read())


def test_smoke_workflow_is_valid_yaml_new() -> None:
    data = _yaml()
    assert "jobs" in data
    assert "smoke" in data["jobs"]


def test_no_workflow_run_trigger_new() -> None:
    data = _yaml()
    triggers = data[True]
    assert "workflow_run" not in triggers
    assert set(triggers.keys()) == {"workflow_dispatch"}


def test_manual_trigger_remains_new() -> None:
    data = _yaml()
    triggers = data[True]
    assert "workflow_dispatch" in triggers
    assert "expected_sha" in triggers["workflow_dispatch"]["inputs"]


def test_artifact_upload_uses_if_always_new() -> None:
    data = _yaml()
    steps = data["jobs"]["smoke"]["steps"]
    upload_steps = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")]

    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["name"] == "production-smoke-report"
    assert upload_steps[0].get("if") == "always()"


def test_smoke_step_never_fails_the_step_directly_new() -> None:
    """The smoke-running step must capture its own exit code and always
    `exit 0`, so downstream artifact-upload/Telegram/summary steps are never
    skipped by an early step failure — the real result is enforced later."""
    text = _read()
    run_smoke_idx = text.index("name: Run production smoke")
    upload_idx = text.index("name: Upload production smoke artifacts")
    section = text[run_smoke_idx:upload_idx]

    assert "smoke_status=success" in section
    assert "smoke_status=failed" in section
    assert "exit 0" in section


def test_telegram_step_isolated_from_smoke_exit_code_new() -> None:
    text = _read()
    telegram_idx = text.index("name: Send Telegram smoke notification")
    write_summary_idx = text.index("name: Write result summary")
    section = text[telegram_idx:write_summary_idx]

    assert "set +e" in section
    assert "telegram_notification_status=success" in section
    assert "telegram_notification_status=failed" in section
    assert "telegram_notification_status=not_configured" in section
    # The step's run script must always exit 0 regardless of Telegram
    # delivery outcome — find the last "exit 0" and confirm nothing but
    # blank lines/the next step header follows it within this section.
    last_exit_idx = section.rindex("exit 0")
    tail = section[last_exit_idx + len("exit 0"):].strip().lstrip("-").strip()
    assert tail == "" or tail.startswith("name:")


def test_telegram_step_runs_with_if_always_new() -> None:
    data = _yaml()
    steps = data["jobs"]["smoke"]["steps"]
    telegram_steps = [s for s in steps if s.get("name") == "Send Telegram smoke notification"]

    assert len(telegram_steps) == 1
    assert telegram_steps[0].get("if") == "always()"


def test_final_result_enforced_by_dedicated_step_new() -> None:
    """A single, final step must be the only place that turns a failed smoke
    result into a failed workflow — not embedded inside the smoke-running
    step or the Telegram step."""
    data = _yaml()
    steps = data["jobs"]["smoke"]["steps"]
    enforce_steps = [s for s in steps if s.get("name") == "Enforce smoke result"]

    assert len(enforce_steps) == 1
    assert enforce_steps[0].get("if") == "always()"
    assert steps[-1]["name"] == "Enforce smoke result"


def test_enforce_step_uses_smoke_status_not_telegram_status_new() -> None:
    text = _read()
    enforce_idx = text.index("name: Enforce smoke result")
    section = text[enforce_idx:]

    assert "SMOKE_STATUS" in section
    assert "TELEGRAM_STATUS" not in section
    assert 'if [ "${SMOKE_STATUS:-failed}" != "success" ]; then' in section
    assert "exit 1" in section


def test_summary_reports_both_statuses_new() -> None:
    text = _read()
    summary_idx = text.index("name: Write result summary")
    enforce_idx = text.index("name: Enforce smoke result")
    section = text[summary_idx:enforce_idx]

    assert "smoke_status:" in section
    assert "telegram_notification_status:" in section
    assert "GITHUB_STEP_SUMMARY" in section


def test_missing_summary_file_has_explicit_fallback_new() -> None:
    text = _read()
    telegram_idx = text.index("name: Send Telegram smoke notification")
    section = text[telegram_idx:telegram_idx + 2000]

    assert "smoke workflow did not produce a summary file" in section


def test_notification_includes_sha_and_run_url_new() -> None:
    text = _read()
    assert "EXPECTED_SHA" in text
    assert "GITHUB_RUN_URL" in text
    assert "production-smoke-report" in text
