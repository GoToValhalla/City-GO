#!/usr/bin/env python3
"""Check production API endpoints and build readable operations reports."""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ExpectedResponse = Literal["any", "html", "json"]


@dataclass(frozen=True)
class CheckSpec:
    name: str
    label: str
    method: str
    path: str
    auth: str = "public"
    body: str | None = None
    expected: ExpectedResponse = "json"


@dataclass(frozen=True)
class CheckResult:
    spec: CheckSpec
    url: str
    status: int | None
    elapsed_ms: int
    body: str
    content_type: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and self.status < 400 and self.error is None


def _base_url(host: str) -> str:
    host = host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
    return f"http://{host}"


def _run_url() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.getenv("GITHUB_REPOSITORY", "GoToValhalla/City-GO")
    run_id = os.getenv("GITHUB_RUN_ID", "unknown")
    return f"{server}/{repo}/actions/runs/{run_id}"


def _short_body(body: str, limit: int = 500) -> str:
    compact = " ".join((body or "").replace("\r", " ").split())
    if not compact:
        return "пустой ответ"
    return compact[:limit] + ("…" if len(compact) > limit else "")


def _looks_like_html(result: CheckResult | None) -> bool:
    if result is None:
        return False
    content_type = result.content_type.lower()
    body = (result.body or "").lstrip().lower()
    return "text/html" in content_type or body.startswith("<!doctype html") or body.startswith("<html")


def _looks_like_citygo_spa(result: CheckResult | None) -> bool:
    if not _looks_like_html(result):
        return False
    body = (result.body or "").lower()
    return "<title>city go</title>" in body or "/assets/index-" in body


def _response_excerpt(result: CheckResult) -> str:
    if _looks_like_citygo_spa(result):
        return "HTML frontend index.html City GO вместо JSON API. Полный HTML скрыт из уведомления."
    if _looks_like_html(result):
        return _short_body(result.body)
    return _short_body(result.body)


def _url_for(base_url: str, path: str) -> str:
    if path.startswith(":"):
        return f"{base_url}{path}"
    return f"{base_url}{path}"


def _semantic_error(spec: CheckSpec, *, body: str, content_type: str) -> str | None:
    normalized_type = content_type.lower()
    normalized_body = body.lstrip().lower()
    is_html = "text/html" in normalized_type or normalized_body.startswith("<!doctype html") or normalized_body.startswith("<html")
    if spec.expected == "json" and is_html:
        return "ожидали JSON API, но получили frontend HTML"
    if spec.expected == "html" and not is_html:
        return "ожидали HTML frontend, но ответ не похож на HTML"
    return None


def run_check(spec: CheckSpec, *, base_url: str, admin_token: str) -> CheckResult:
    url = _url_for(base_url, spec.path)
    headers = {}
    data = None
    if spec.auth == "admin":
        if not admin_token:
            return CheckResult(
                spec=spec,
                url=url,
                status=None,
                elapsed_ms=0,
                body="",
                content_type="",
                error="ADMIN_API_TOKEN не задан в GitHub Secrets",
            )
        headers["Authorization"] = f"Bearer {admin_token}"
    if spec.body is not None:
        headers["Content-Type"] = "application/json"
        data = spec.body.encode("utf-8")

    started = time.monotonic()
    request = urllib.request.Request(url, data=data, headers=headers, method=spec.method)
    try:
        with urllib.request.urlopen(request, timeout=35) as response:  # noqa: S310 - production monitor URL from secrets
            body = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("content-type", "")
            return CheckResult(
                spec=spec,
                url=url,
                status=int(response.status),
                elapsed_ms=int((time.monotonic() - started) * 1000),
                body=body,
                content_type=content_type,
                error=_semantic_error(spec, body=body, content_type=content_type),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return CheckResult(
            spec=spec,
            url=url,
            status=int(exc.code),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            body=body,
            content_type=exc.headers.get("content-type", "") if exc.headers else "",
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - monitor must report any network/runtime failure
        return CheckResult(
            spec=spec,
            url=url,
            status=None,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            body="",
            content_type="",
            error=str(exc),
        )


def default_checks() -> list[CheckSpec]:
    route_body = json.dumps(
        {
            "lat": 40.1792,
            "lng": 44.4991,
            "start_address": None,
            "start_source": "city_center",
            "start": {"type": "city_center", "lat": 40.1792, "lng": 44.4991, "address": None},
            "build_mode": "by_categories",
            "time_budget_minutes": 240,
            "time_of_day": None,
            "route_time_mode": "flexible",
            "interests": ["coffee", "food", "walk"],
            "avoided_categories": [],
            "excluded_place_ids": [],
            "budget_level": None,
            "pace_mode": None,
            "is_visiting": False,
            "city_id": "yerevan",
            "visit_city_id": None,
            "visit_days": None,
            "user_id": "monitor",
        },
        ensure_ascii=False,
    )
    return [
        CheckSpec("frontend", "Главная страница frontend", "GET", "/", expected="html"),
        CheckSpec("api_health_proxy", "Health через nginx /api", "GET", "/api/health"),
        CheckSpec("api_ready_proxy", "Ready через nginx /api", "GET", "/api/ready"),
        CheckSpec("admin_overview_proxy", "Админка: обзор", "GET", "/api/admin/overview", "admin"),
        CheckSpec("admin_metrics_proxy", "Админка: метрики", "GET", "/api/admin/metrics/summary", "admin"),
        CheckSpec("admin_coverage_proxy", "Админка: покрытие данных", "GET", "/api/admin/coverage/summary?limit=5", "admin"),
        CheckSpec("admin_verification_proxy", "Админка: очередь проверки", "GET", "/api/admin/place-verifications/summary", "admin"),
        CheckSpec("admin_route_eligibility_proxy", "Админка: готовность мест к маршрутам", "GET", "/api/admin/routes/eligibility?limit=1&city_slug=yerevan", "admin"),
        CheckSpec("admin_route_readiness_proxy", "Админка: готовность маршрутов", "GET", "/api/admin/routes/readiness?limit=1", "admin"),
        CheckSpec("route_preview_yerevan_proxy", "Route preview через nginx", "POST", "/api/v1/user-routes/preview", body=route_body),
    ]


def _endpoint_path(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    return path + (f"?{parsed.query}" if parsed.query else "")


def _status_text(result: CheckResult) -> str:
    if result.status is None:
        return "нет ответа"
    return f"HTTP {result.status}"


def _status_code_text(result: CheckResult) -> str:
    if result.status is None:
        return "нет ответа"
    return str(result.status)


def _probable_reason(result: CheckResult) -> str:
    if _looks_like_citygo_spa(result):
        return "API-запрос попал в frontend SPA. Частые причины: неверный URL, redirect без /api, trailing slash или nginx proxy не совпадает с backend route."
    if _looks_like_html(result) and result.spec.expected == "json":
        return "API-запрос вернул HTML вместо JSON. Нужно проверить routing/proxy/redirect, а не только backend logs."
    if result.status is None:
        return "нет соединения с endpoint, таймаут, закрытый порт или сервис не слушает запрос."
    if result.status == 401 or result.status == 403:
        return "ошибка авторизации: ADMIN_API_TOKEN не совпадает с production или endpoint защищён другим способом."
    if result.status == 404:
        return "endpoint отсутствует, nginx проксирует не туда или backend-роут не подключён."
    if result.status == 422:
        return "контракт monitor-запроса не совпадает с backend-валидацией."
    if result.status >= 500:
        return "ошибка backend, базы данных или тяжёлого запроса; нужны backend logs и проверка /ready."
    if result.status >= 400:
        return "запрос отвергнут приложением или прокси; проверить параметры и права доступа."
    return "семантическая проверка ответа не совпала с ожиданием monitor."


def _recommended_action(result: CheckResult) -> str:
    if _looks_like_html(result) and result.spec.expected == "json":
        return "проверить точный API path, trailing slash, nginx location /api/ и redirect FastAPI; для API monitor endpoint должен возвращать JSON, не index.html."
    if result.status is None:
        return "проверить доступность порта, nginx, backend-контейнер и сетевые таймауты."
    if result.status in {401, 403}:
        return "сверить ADMIN_API_TOKEN в GitHub Secrets и production .env, затем перезапустить deploy."
    if result.status == 404:
        return "проверить nginx location, router registration и актуальность URL в monitor."
    if result.status == 422:
        return "обновить payload monitor-запроса или backend-схему, чтобы контракт совпал."
    if result.status >= 500:
        return "открыть backend logs за время прогона, проверить PostgreSQL readiness, долгие запросы и последние миграции."
    return "открыть лог workflow и ответ endpoint."


def _ok_summary(results: list[CheckResult]) -> list[str]:
    ok = [item for item in results if item.ok]
    return [f"• {item.spec.label}: HTTP {item.status}, {item.elapsed_ms} мс" for item in sorted(ok, key=lambda x: x.elapsed_ms, reverse=True)[:3]]


def build_report(results: list[CheckResult]) -> str:
    failures = [item for item in results if not item.ok]
    passed = len(results) - len(failures)
    status_icon = "✅" if not failures else "❌"
    lines = [
        f"{status_icon} CITY GO · API MONITOR",
        f"{status_icon} City GO · API monitor {'прошёл production-проверку' if not failures else 'нашёл ошибки'}",
        f"Статус: {'API стабилен' if not failures else 'API не прошёл production-проверку'}",
        f"Хост: {os.getenv('PROD_HOST', 'unknown')}",
        f"Итог: {passed}/{len(results)} проверок успешно" + (f", {len(failures)} упало" if failures else ""),
        "",
    ]
    if failures:
        lines.append("Сломанные проверки:")
        for index, result in enumerate(failures[:6], start=1):
            lines.extend([
                f"{index}. {result.spec.label}",
                f"   Запрос: {result.spec.method} {_endpoint_path(result.url)}",
                f"   Endpoint: {result.spec.method} {result.spec.path}",
                f"   Факт: {_status_text(result)} за {result.elapsed_ms} мс",
                f"   HTTP: {_status_code_text(result)}",
                f"   Время: {result.elapsed_ms} мс",
                f"   Content-Type: {result.content_type or 'не указан'}",
                f"   Техническая причина: {result.error or 'нет'}",
                f"   Вероятная причина: {_probable_reason(result)}",
                f"   Причина: {_probable_reason(result)}",
                f"   Что делать: {_recommended_action(result)}",
                f"   Ответ: {_response_excerpt(result)}",
            ])
        if len(failures) > 6:
            lines.append(f"Ещё упавших проверок: {len(failures) - 6}")
        lines.append("")
    ok_lines = _ok_summary(results)
    if ok_lines:
        lines.append("Самые медленные успешные проверки:")
        lines.extend(ok_lines)
        lines.append("")
    lines.append("Следующий шаг: открыть GitHub run и логи соответствующего слоя. При HTML вместо JSON сначала проверять routing/nginx/redirect, при 500 — backend logs и /ready.")
    lines.append(f"GitHub Actions: {_run_url()}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check City GO production API endpoints")
    parser.add_argument("--host", required=True, help="Production host, e.g. 1.2.3.4")
    parser.add_argument("--admin-token", default="", help="Admin API token")
    parser.add_argument("--notification-file", default="", help="Optional file for Telegram notification text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = _base_url(args.host)
    results = [run_check(spec, base_url=base_url, admin_token=args.admin_token) for spec in default_checks()]
    report = build_report(results)
    print(report)
    if args.notification_file:
        Path(args.notification_file).write_text(report, encoding="utf-8")
    return 0 if all(item.ok for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
