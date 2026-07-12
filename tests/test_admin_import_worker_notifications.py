import allure
import pytest

from data.scripts import run_admin_import_worker as worker
from tests.allure_support import given, scenario, then, when

pytestmark = [pytest.mark.unit, pytest.mark.regression]


@scenario(
    "Import-worker уведомляет о падении внешнего цикла и восстановлении",
    epic="Платформа данных",
    feature="Импорт и обогащение",
    story="Наблюдаемость import-worker",
    severity=allure.severity_level.CRITICAL,
)
def test_worker_alerts_on_outer_failure_and_recovery(monkeypatch) -> None:
    alerts = []
    calls = iter([RuntimeError("database unavailable"), {"queue": {"queued": 2}}])

    with given("первая итерация worker падает до обработки job, а вторая успешна"):
        def run_jobs(**_kwargs):
            result = next(calls)
            if isinstance(result, Exception):
                raise result
            return result
        monkeypatch.setattr(worker, "run_queued_import_jobs", run_jobs)
        monkeypatch.setattr(worker, "send_admin_alert", lambda **kwargs: alerts.append(kwargs) or {"sent": True})
        monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
        monkeypatch.setattr(worker, "_STOP", False)

    with when("worker выполняет две итерации"):
        worker.run_worker_loop(limit=1, sleep_seconds=5, max_iterations=2)

    with then("первая ошибка не проглатывается и отправляется аварийное уведомление"):
        assert alerts[0]["title"] == "Import worker job failed"
        assert alerts[0]["details"]["consecutive_failures"] == 1

    with then("после успешной итерации отправляется уведомление о восстановлении"):
        assert alerts[1]["title"] == "Import-worker восстановлен"
        assert alerts[1]["details"]["previous_failures"] == 1


def test_worker_stops_when_backend_health_check_fails(monkeypatch) -> None:
    """Post-OOM-incident invariant: the worker must never keep claiming jobs
    once backend is confirmed unhealthy — it must stop immediately and exit,
    not silently keep running against a dead backend."""
    calls = []
    alerts = []

    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: calls.append(1) or {"queue": {}})
    monkeypatch.setattr(worker, "send_admin_alert", lambda **kwargs: alerts.append(kwargs) or {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: False)
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker, "_STOP", False)

    worker.run_worker_loop(limit=1, sleep_seconds=5, max_iterations=5, health_url="http://backend:8000/ready")

    assert calls == []
    assert alerts[0]["title"] == "Import-worker остановлен: backend недоступен"
    assert alerts[0]["level"] == "error"


def test_worker_processes_jobs_when_backend_is_healthy(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: calls.append(1) or {"queue": {}})
    monkeypatch.setattr(worker, "send_admin_alert", lambda **kwargs: {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: True)
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker, "_STOP", False)

    worker.run_worker_loop(limit=1, sleep_seconds=5, max_iterations=2, health_url="http://backend:8000/ready")

    assert len(calls) == 2


def test_backend_is_healthy_true_for_2xx_response(monkeypatch) -> None:
    class _FakeResponse:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(worker.urllib.request, "urlopen", lambda *_a, **_k: _FakeResponse())

    assert worker.backend_is_healthy("http://backend:8000/ready") is True


def test_backend_is_healthy_false_on_connection_error(monkeypatch) -> None:
    def raise_connection_error(*_args, **_kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(worker.urllib.request, "urlopen", raise_connection_error)

    assert worker.backend_is_healthy("http://backend:8000/ready") is False


def test_backend_is_healthy_true_when_no_url_configured() -> None:
    assert worker.backend_is_healthy("") is True


def test_worker_stops_after_max_runtime_seconds(monkeypatch) -> None:
    """The worker must not run unbounded — a configured max runtime must stop
    the loop even if the backend stays healthy and jobs keep succeeding."""
    calls = []
    alerts = []
    fake_time = {"now": 0.0}

    monkeypatch.setattr(worker, "run_queued_import_jobs", lambda **_kwargs: calls.append(1) or {"queue": {}})
    monkeypatch.setattr(worker, "send_admin_alert", lambda **kwargs: alerts.append(kwargs) or {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: True)
    monkeypatch.setattr(worker, "_STOP", False)

    def fake_monotonic():
        return fake_time["now"]

    def fake_sleep(seconds):
        fake_time["now"] += seconds

    monkeypatch.setattr(worker.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(worker.time, "sleep", fake_sleep)

    worker.run_worker_loop(limit=1, sleep_seconds=100, max_iterations=50, max_runtime_seconds=250)

    assert len(calls) <= 3
    assert alerts[-1]["title"] == "Import-worker остановлен по таймауту"


def test_worker_loop_surfaces_queued_locked_in_container_log_new(monkeypatch, capsys) -> None:
    """A queued_locked result must not be treated as a silent success — it
    must be printed to the worker's own stderr/container log immediately,
    in addition to the SystemLog/Telegram alert already sent inside
    run_queued_import_jobs, so operators see it without needing to check
    Telegram or query SystemLog directly."""
    monkeypatch.setattr(
        worker,
        "run_queued_import_jobs",
        lambda **_kwargs: {"queue": {}, "queued_locked": 1},
    )
    monkeypatch.setattr(worker, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: True)
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker, "_STOP", False)

    worker.run_worker_loop(limit=1, sleep_seconds=5, max_iterations=1, health_url="http://backend:8000/ready")

    captured = capsys.readouterr()
    assert "import_worker_queued_jobs_locked" in captured.err
    assert "count=1" in captured.err


def test_worker_loop_stays_silent_when_no_jobs_are_locked_new(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        worker,
        "run_queued_import_jobs",
        lambda **_kwargs: {"queue": {}, "queued_locked": 0},
    )
    monkeypatch.setattr(worker, "send_admin_alert", lambda **_kwargs: {"sent": True})
    monkeypatch.setattr(worker, "backend_is_healthy", lambda *_a, **_k: True)
    monkeypatch.setattr(worker.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(worker, "_STOP", False)

    worker.run_worker_loop(limit=1, sleep_seconds=5, max_iterations=1, health_url="http://backend:8000/ready")

    captured = capsys.readouterr()
    assert "import_worker_queued_jobs_locked" not in captured.err
