import json
from pathlib import Path

import scripts.catalog_data_monitor as catalog_monitor
from scripts.api_error_monitor import CheckResult, CheckSpec, failure_report as api_failure_report
from scripts.catalog_data_monitor import HttpResult, failure_report as catalog_failure_report
from services.osm_import_taxonomy import category_from_osm_tags, unsupported_tag_reason


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


def test_api_monitor_html_instead_of_json_is_reported_as_routing_issue(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "321")

    failed = CheckResult(
        spec=CheckSpec("places", "Каталог: места", "GET", "/api/places/"),
        url="http://2.27.4.31/api/places/",
        status=200,
        elapsed_ms=614,
        body='<!doctype html><html lang="ru"><head><title>City GO</title></head></html>',
        content_type="text/html",
        error="ожидали JSON API, но получили frontend HTML",
    )

    text = api_failure_report(host="2.27.4.31", results=[failed])

    assert "Статус: API не прошёл production-проверку" in text
    assert "Факт: HTTP 200 за 614 мс" in text
    assert "ожидали JSON API, но получили frontend HTML" in text
    assert "API-запрос попал в frontend SPA" in text
    assert "routing/nginx/redirect" in text
    assert "HTML frontend index.html City GO вместо JSON API" in text
    assert "<!doctype html>" not in text
    assert "visibility" not in text.lower()


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
    assert "Техническая причина: семантическая проверка данных не прошла" in text
    assert "Что это значит: HTTP 200 не означает рабочий каталог" in text
    assert "Что делать: проверить cities.is_active" in text
    assert "GitHub Actions: https://github.com/GoToValhalla/City-GO/actions/runs/456" in text
    assert "HTTP может отвечать 200, но список городов или мест пуст" not in text
    assert "catalog data is unavailable" not in text


def test_catalog_monitor_html_places_response_is_not_reported_as_database_issue(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    monkeypatch.setenv("GITHUB_RUN_ID", "789")

    result = HttpResult(
        method="GET",
        url="http://2.27.4.31/api/places/?city_slug=arkhangelsk&limit=1&offset=0",
        status=200,
        elapsed_ms=614,
        body='<!doctype html><html lang="ru"><head><title>City GO</title></head></html>',
        content_type="text/html",
    )

    text = catalog_failure_report(
        host="2.27.4.31",
        result=result,
        problem="список мест для города arkhangelsk вернул frontend HTML вместо JSON",
        meaning="запрос не дошёл до нужного backend API или был перенаправлен на SPA. Это проблема routing/URL/trailing slash/nginx, а не доказательство пустой БД.",
        action="проверить API URL, trailing slash, nginx location /api/ и redirect FastAPI.",
    )

    assert "Проблема: список мест для города arkhangelsk вернул frontend HTML вместо JSON" in text
    assert "Техническая причина: ожидали JSON API, но получили frontend index.html" in text
    assert "Это проблема routing/URL/trailing slash/nginx" in text
    assert "не доказательство пустой БД" in text
    assert "HTML frontend index.html City GO вместо JSON API" in text
    assert "<!doctype html>" not in text
    assert "visibility-фильтров" not in text


def test_catalog_monitor_uses_trailing_slash_for_places_api(monkeypatch) -> None:
    calls: list[str] = []

    def fake_http_get(url: str, *, timeout: int = 25) -> HttpResult:
        calls.append(url)
        if "/api/cities/available" in url:
            return HttpResult(
                method="GET",
                url=url,
                status=200,
                elapsed_ms=20,
                body='{"items":[{"slug":"arkhangelsk"}]}',
                content_type="application/json",
            )
        return HttpResult(
            method="GET",
            url=url,
            status=200,
            elapsed_ms=30,
            body='{"items":[{"id":1}],"total":1}',
            content_type="application/json",
        )

    monkeypatch.setattr(catalog_monitor, "http_get", fake_http_get)

    exit_code, text = catalog_monitor.run_monitor("2.27.4.31")

    assert exit_code == 0
    assert "публичный каталог доступен" in text
    assert calls[1] == "https://2.27.4.31/api/places/?city_slug=arkhangelsk&limit=1&offset=0"


def test_known_missing_poi_seed_contains_kutaisi_regression_set() -> None:
    payload = json.loads(Path("data/config/known_missing_poi.json").read_text(encoding="utf-8"))
    kutaisi = next(city for city in payload["cities"] if city["city"] == "kutaisi")
    slugs = {item["slug"] for item in kutaisi["items"]}

    assert len(kutaisi["items"]) == 7
    assert {
        "bagrati-cathedral",
        "motsameta-monastery",
        "gelati-monastery",
        "sanapiro",
        "kebaby-bikentiya",
        "kutaisi-amusement-park",
        "sataplia-cave",
    } <= slugs


def test_osm_taxonomy_covers_kutaisi_gap_classes() -> None:
    assert category_from_osm_tags({"historic": "monastery"}) == "culture"
    assert category_from_osm_tags({"building": "cathedral"}) == "culture"
    assert category_from_osm_tags({"natural": "cave_entrance"}) == "walk"
    assert category_from_osm_tags({"waterway": "waterfall"}) == "walk"
    assert category_from_osm_tags({"tourism": "theme_park"}) == "park"
    assert category_from_osm_tags({"leisure": "amusement_arcade"}) == "park"
    assert unsupported_tag_reason({"historic": "monastery"}) is None
