from scripts.api_error_monitor import CheckResult, CheckSpec, failure_report as api_failure_report
from scripts.catalog_data_monitor import HttpResult, failure_report as catalog_failure_report


def test_api_monitor_failure_message_is_actionable(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")

    failed = CheckResult(
        spec=CheckSpec("admin_places", "Админка: места", "GET", "/api/admin/places", "admin"),
        url="http://2.27.4.31/api/admin/places",
        status=500,
        elapsed_ms=2450,
        body='{"detail":"database is unavailable"}',
        content_type="application/json",
        error="HTTP Error 500: Internal Server Error",
    )
    ok = CheckResult(
        spec=CheckSpec("health", "Health через nginx /api", "GET", "/api/health"),
        url="http://2.27.4.31/api/health",
        status=200,
        elapsed_ms=120,
        body='{"ok":true}',
        content_type="application/json",
    )

    text = api_failure_report(host="2.27.4.31", results=[failed, ok])

    assert "❌ CITY GO · API MONITOR" in text
    assert "Итог: 1/2 проверок успешно, 1 упало" in text
    assert "Запрос: GET /api/admin/places" in text
    assert "Факт: HTTP 500 за 2450 мс" in text
    assert "Вероятная причина:" in text
    assert "Что делать:" in text
    assert "Ответ: {\"detail\":\"database is unavailable\"}" in text
    assert "GitHub Actions: https://github.com/GoToValhalla/City-GO/actions/runs/123" in text
    assert "No report captured" not in text
    assert "detected HTTP 4xx/5xx" not in text


def test_catalog_monitor_empty_city_message_explains_semantic_failure(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "456")

    result = HttpResult(
        method="GET",
        url="http://2.27.4.31/api/cities/available?include_draft=true",
        status=200,
        elapsed_ms=180,
        body='{"items":[]}',
        content_type="application/json",
    )

    text = catalog_failure_report(
        host="2.27.4.31",
        result=result,
        problem="API вернул 0 доступных городов",
        meaning="HTTP 200 не означает рабочий каталог: витрина фактически пустая.",
        action="проверить cities.is_active, launch_status и feature flags.",
    )

    assert "❌ CITY GO · CATALOG DATA MONITOR" in text
    assert "Сценарий: пользователь открывает город и список мест" in text
    assert "Проблема: API вернул 0 доступных городов" in text
    assert "Запрос: GET /api/cities/available?include_draft=true" in text
    assert "Факт: HTTP 200 за 180 мс" in text
    assert "Техническая ошибка: семантическая проверка данных не прошла" in text
    assert "Что это значит: HTTP 200 не означает рабочий каталог" in text
    assert "Что делать: проверить cities.is_active" in text
    assert "GitHub Actions: https://github.com/GoToValhalla/City-GO/actions/runs/456" in text
    assert "HTTP может отвечать 200, но список городов или мест пуст" not in text
    assert "catalog data is unavailable" not in text
