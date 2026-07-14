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


def test_run_mode_env_defaults_to_safe_one_job_new(monkeypatch) -> None:
    monkeypatch.delenv("IMPORT_WORKER_RUN_MODE", raising=False)
    monkeypatch.delenv("IMPORT_WORKER_CITY_SLUG", raising=False)
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {"processed": 0, "failed": 0, "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["dry_run"] is False
    assert calls[0]["city_slug"] is None


def test_unknown_run_mode_falls_back_to_safe_one_job_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "bogus_mode")
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {"processed": 0, "failed": 0, "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0
    assert calls[0]["dry_run"] is False


def test_city_slug_env_is_passed_to_run_queued_import_jobs_new(monkeypatch) -> None:
    monkeypatch.setenv("IMPORT_WORKER_RUN_MODE", "safe_one_job")
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "astrakhan")
    calls = []
    monkeypatch.setattr(
        worker, "run_queued_import_jobs",
        lambda **kwargs: calls.append(kwargs) or {"processed": 1, "failed": 0, "queue": {}},
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
        lambda **kwargs: seen_city_slugs.append(kwargs.get("city_slug")) or {"processed": 1, "failed": 0, "queue": {}},
    )

    worker.main()

    assert seen_city_slugs == ["kutaisi"]


def test_safe_one_job_mode_calls_run_queued_import_jobs_exactly_once_new(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {"processed": 1, "failed": 0, "queue": {}})

    worker.main()

    assert len(calls) == 1
    assert calls[0]["limit"] == 1


def test_safe_one_job_ignores_higher_batch_limit_env_new(monkeypatch) -> None:
    """IMPORT_WORKER_BATCH_LIMIT can only lower the one-job floor, never
    raise it, in safe_one_job/dry_run modes."""
    monkeypatch.setenv("IMPORT_WORKER_BATCH_LIMIT", "5")
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **kwargs: calls.append(kwargs) or {"processed": 1, "failed": 0, "queue": {}})

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


def test_succeeds_when_city_slug_job_is_claimed_but_fails_new(monkeypatch) -> None:
    """A claimed-but-failed job still counts as 'found a matching job' —
    the no-matching-job failure must not fire when the real problem was a
    job execution error, which already has its own alerting/logging path."""
    monkeypatch.setenv("IMPORT_WORKER_CITY_SLUG", "astrakhan")
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"processed": 0, "failed": 1, "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0


def test_no_city_slug_set_never_fails_on_empty_queue_new(monkeypatch) -> None:
    """Without city_slug, an empty queue is normal idle behavior, not a
    failure — only a city_slug-targeted run with zero matches must fail."""
    monkeypatch.delenv("IMPORT_WORKER_CITY_SLUG", raising=False)
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: {"processed": 0, "failed": 0, "queue": {}})

    exit_code = worker.main()

    assert exit_code == 0
