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
