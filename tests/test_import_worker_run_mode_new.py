"""Regression tests for the typed run_mode/city_slug import-worker inputs:
safe_one_job/dry_run/diagnostics_only, city targeting, the one-job limit,
and non-mutating behavior in dry_run/diagnostics_only."""

from __future__ import annotations

import pytest

from data.scripts import run_admin_import_worker as worker


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker, "_STOP", False)
    monkeypatch.setattr(worker, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: True)


def _claimed(job_id: int = 1, terminal_status: str = "success", **overrides) -> dict:
    payload = {
        "processed": 1 if terminal_status != "failed" else 0,
        "failed": 1 if terminal_status == "failed" else 0,
        "queue": {},
        "claimed_jobs": [{"job_id": job_id, "terminal_status": terminal_status}],
    }
    payload.update(overrides)
    return payload


def test_run_mode_env_defaults_to_safe_one_job_new(monkeypatch) -> None:
    monkeypatch.delenv("IMPORT_WORKER_RUN_MODE", raising=False)
    monkeypatch.delenv("IMPORT_WORKER_CITY_SLUG", raising=False)
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or _claimed())

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["dry_run"] is False
    assert calls[0]["city_slug"] is None


def test_unknown_run_mode_falls_back_to_safe_one_job_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "bogus_mode")
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or _claimed())

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["dry_run"] is False


def test_city_slug_env_is_passed_to_run_queued_import_jobs_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "safe_one_job")
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "astrakhan")
    calls = []
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **kwargs: calls.append(kwargs) or _claimed(),
    )

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["city_slug"] == "astrakhan"


def test_never_processes_unrelated_city_when_city_slug_set_new(monkeypatch) -> None:
    """The worker script itself must forward city_slug on every call — the
    actual cross-city exclusion is enforced in run_queued_import_jobs
    (services/admin_city_import_tasks.py), verified separately; here we
    confirm the script never silently drops or widens the filter."""
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "kutaisi")
    seen_city_slugs = []
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **kwargs: seen_city_slugs.append(kwargs.get("city_slug")) or _claimed(),
    )

    worker.main()

    assert seen_city_slugs == ["kutaisi"]


def test_safe_one_job_mode_calls_run_queued_import_jobs_exactly_once_new(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or _claimed())

    worker.main()

    assert len(calls) == 1
    assert calls[0]["limit"] == 1


def test_safe_one_job_ignores_higher_batch_limit_env_new(monkeypatch) -> None:
    """IMPORT_WORKER_BATCH_LIMIT can only lower the one-job floor, never
    raise it, in safe_one_job/dry_run modes."""
    monkeypatch.setenv("IMPORT_WORKER_BATCH_LIMIT", "5")
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or _claimed())

    worker.main()

    assert calls[0]["limit"] == 1


def test_dry_run_mode_never_mutates_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "dry_run")
    calls = []
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **kwargs: calls.append(kwargs) or {"would_process": [{"job_id": 1, "city_id": 2, "source": "full_import"}], "queue": {}},
    )

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["dry_run"] is True


def test_dry_run_with_no_matching_job_reports_nothing_would_process_new(monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "dry_run")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"would_process": [], "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0
    assert "would_process=[]" in capsys.readouterr().out


def test_diagnostics_only_mode_never_calls_run_queued_import_jobs_new(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "diagnostics_only")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {})
    monkeypatch.setattr(worker, "import_queue_summary", lambda _db: {"total": 3, "active_total": 1})

    class _FakeSession:
        def __enter__(self):
            return "fake-db"

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(worker, "SessionLocal", lambda: _FakeSession())

    exit_code = worker.main()

    assert exit_code == 0
    assert calls == []


def test_diagnostics_only_reports_city_slug_filter_new(monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "diagnostics_only")
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "batumi")
    monkeypatch.setattr(worker, "import_queue_summary", lambda _db: {"total": 0})

    class _FakeSession:
        def __enter__(self):
            return "fake-db"

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(worker, "SessionLocal", lambda: _FakeSession())

    exit_code = worker.main()

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "city_slug_filter" in out
    assert "batumi" in out


def test_fails_clearly_when_city_slug_has_no_queued_job_new(monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "safe_one_job")
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "nowhere")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"processed": 0, "failed": 0, "queue": {}})

    exit_code = worker.main()

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "no_matching_queued_job" in err
    assert "nowhere" in err


def test_succeeds_when_city_slug_job_is_claimed_and_reaches_terminal_status_new(monkeypatch) -> None:
    """A claimed job that reaches a terminal status (even "failed", a real
    job-execution outcome with its own alerting/logging path) is not a
    no-matching-job condition — the run reports processed=True and exits 0."""
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "astrakhan")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: _claimed(terminal_status="failed"))

    exit_code = worker.main()

    assert exit_code == 0


def test_safe_one_job_fails_on_empty_queue_even_without_city_slug_new(monkeypatch) -> None:
    """safe_one_job must fail if no matching job was claimed or processed —
    a healthy-looking run that quietly claimed nothing is not success,
    regardless of whether city_slug was set. (Superseded the previous
    "never fails on empty queue" contract, which was exactly the silent
    no-progress-reported-as-success defect this task fixes.)"""
    monkeypatch.delenv("IMPORT_WORKER_CITY_SLUG", raising=False)
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"processed": 0, "failed": 0, "queue": {}, "claimed_jobs": []})

    exit_code = worker.main()

    assert exit_code == 1


def test_dry_run_does_not_fail_on_empty_queue_new(monkeypatch) -> None:
    """dry_run is exempt from the no-claim failure: reporting an empty
    queue is dry_run's correct, successful outcome since it never claims
    anything by design."""
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "dry_run")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"would_process": [], "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0


def test_fails_when_claimed_job_never_reaches_terminal_status_new(monkeypatch, capsys) -> None:
    """Max runtime reached with a claimed job that never finished (no
    terminal status) must fail — a stalled job looks identical to a
    healthy run unless this is checked explicitly."""
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **_kwargs: {"processed": 0, "failed": 0, "queue": {}, "claimed_jobs": [{"job_id": 42, "terminal_status": "running"}]},
    )

    exit_code = worker.main()

    assert exit_code == 1
    err = capsys.readouterr().err
    assert "did_not_reach_terminal_status" in err
    assert "job_id=42" in err


def test_outcome_json_includes_all_required_structured_fields_new(monkeypatch, capsys) -> None:
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "almaty")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: _claimed(job_id=7, terminal_status="success"))

    exit_code = worker.main()

    assert exit_code == 0
    out = capsys.readouterr().out
    outcome_line = next(line for line in out.splitlines() if line.startswith("import_worker_outcome "))
    import json as _json
    payload = _json.loads(outcome_line.removeprefix("import_worker_outcome "))
    assert payload["requested_city_slug"] == "almaty"
    assert payload["matched_job_id"] == 7
    assert payload["claimed"] is True
    assert payload["processed"] is True
    assert payload["terminal_status"] == "success"
    assert payload["skip_reason"] is None
    assert isinstance(payload["elapsed_seconds"], (int, float))
    assert payload["exit_code"] == 0


def test_safe_one_job_exits_nonzero_when_max_runtime_reached_before_any_claim_new(monkeypatch, capsys) -> None:
    """import_worker_max_runtime_reached firing before run_queued_import_jobs
    is ever called (max_runtime_seconds already elapsed when the loop's
    first check runs) must still exit non-zero — the container exiting 0
    is not sufficient evidence of success on its own."""
    monkeypatch.setenv("IMPORT_WORKER_MAX_RUNTIME_SECONDS", "300")
    calls: list[dict] = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {"processed": 0, "failed": 0, "queue": {}, "claimed_jobs": []})
    # time.monotonic() is called once for started_at, then again inside the
    # loop's runtime check on every subsequent call. Returning a huge value
    # from the second call onward simulates max_runtime already having
    # elapsed by the time the loop first checks — before any job is claimed.
    monotonic_values = iter([0.0] + [10_000.0] * 10)
    monkeypatch.setattr(worker.time, "monotonic", lambda: next(monotonic_values))

    exit_code = worker.main()

    assert exit_code == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "import_worker_max_runtime_reached" in err
    assert "no_matching_queued_job" in err


def test_safe_one_job_exits_nonzero_when_claimed_job_stalls_past_max_runtime_new(monkeypatch, capsys) -> None:
    """A job that gets claimed but never reaches a terminal status before
    max_runtime elapses must exit non-zero, matching the exact stall
    symptom from the original bug report — regardless of the eventual
    container exit code."""
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **_kwargs: {"processed": 0, "failed": 0, "queue": {}, "claimed_jobs": [{"job_id": 99, "terminal_status": "running"}]},
    )

    exit_code = worker.main()

    assert exit_code == 1
