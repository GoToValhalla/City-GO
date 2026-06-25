from scripts.api_error_monitor import CheckResult, CheckSpec, failure_report as api_failure_report
from scripts.catalog_data_monitor import HttpResult, failure_report as catalog_failure_report


def test_api_monitor_report_contains_endpoint_status_reason_and_action() -> None:
    spec = CheckSpec(
        name="admin_overview_proxy",
        label="Админка: обзор",
        method="GET",
        path="/api/admin/overview",
        auth="admin",
    )
    report = api_failure_report(
        host="2.27.4.31",
        results=[
            CheckResult(
                spec=spec,
                url="http://2.27.4.31/api/admin/overview",
                status=500,
                elapsed_ms=734,
                body='{"detail":"database is unavailable"}',
                content_type="application/json",
                error="HTTP Error 500",
            )
        ],
    )

    assert "City GO · API monitor нашёл ошибки" in report
    assert "Endpoint: GET /api/admin/overview" in report
    assert "HTTP: 500" in report
    assert "Причина:" in report
    assert "Что делать:" in report
    assert "No report captured" not in report


def test_catalog_monitor_report_distinguishes_invalid_json_from_empty_catalog() -> None:
    report = catalog_failure_report(
        title="catalog_cities_failed",
        host="2.27.4.31",
        result=HttpResult(
            method="GET",
            url="http://2.27.4.31/api/cities/available?include_draft=true",
            status=502,
            elapsed_ms=120,
            body="<html>Bad gateway</html>",
            content_type="text/html",
            error="HTTP Error 502",
        ),
        problem="не удалось получить список городов: HTTP 502",
        meaning="публичный каталог не может выбрать город; пользователь увидит пустой список или зависание.",
        action="проверить backend, nginx proxy и /api/cities/available; открыть логи backend за время прогона.",
    )

    assert "City GO · Каталог недоступен" in report
    assert "Endpoint: GET /api/cities/available?include_draft=true" in report
    assert "HTTP: 502" in report
    assert "Content-Type: text/html" in report
    assert "Ответ: <html>Bad gateway</html>" in report
    assert "города или места пусты" not in report
