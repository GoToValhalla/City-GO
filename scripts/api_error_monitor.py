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
from typing import Any


@dataclass(frozen=True)
class CheckSpec:
    name: str
    label: str
    method: str
    path: str
    auth: str = "public"
    body: str | None = None


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


def _url_for(base_url: str, path: str) -> str:
    if path.startswith(":"):
        return f"{base_url}{path}"
    return f"{base_url}{path}"


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
            return CheckResult(
                spec=spec,
                url=url,
                status=int(response.status),
                elapsed_ms=int((time.monotonic() - started) * 1000),
                body=body,
                content_type=response.headers.get("content-type", ""),
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
        CheckSpec("frontend", "Главная страница frontend", "GET", "/"),
        CheckSpec("api_health_proxy", "Health через nginx /api", "GET", "/api/health"),
        CheckSpec("backend_health_direct", "Health backend напрямую", "GET", ":8000/health"),
        CheckSpec("admin_overview_proxy", "Админка: обзор", "GET", "/api/admin/overview", "admin"),
        CheckSpec("admin_metrics_proxy", "Админка: метрики", "GET", "/api/admin/metrics/summary", "admin"),
        CheckSpec("admin_coverage_proxy", "Админка: покрытие данных", "GET", "/api/admin/coverage/summary?limit=5", "admin"),
        CheckSpec("admin_verification_proxy", "Админка: очередь проверки", "GET", "/api/admin/place-verifications/summary", "admin"),
        CheckSpec("admin_route_eligibility_proxy", "Админка: готовность мест к маршрутам", "GET", "/api/admin/routes/eligibility?limit=1", "admin"),
        CheckSpec("admin_route_readiness_proxy", "Админка: готовность маршрутов", "GET", "/api/admin/routes/readiness?limit=10", "admin"),
        CheckSpec("admin_overview_backend", "Backend: обзор админки напрямую", "GET", ":8000/admin/overview", "admin"),
        CheckSpec("admin_coverage_backend", "Backend: покрытие напрямую", "GET", ":8000/admin/coverage/summary?limit=5", "admin"),
        CheckSpec("admin_route_readiness_backend", "Backend: готовность маршрутов напрямую", "GET", ":8000/admin/routes/readiness?limit=10", "admin"),
        CheckSpec("route_preview_yerevan_proxy", "Route preview через nginx", "POST", "/api/v1/user-routes/preview", body=route_body),
        CheckSpec("route_preview_yerevan_backend", "Route preview backend напрямую", "POST", ":8000/v1/user-routes/preview", body=route_body),
    ]


def _endpoint_path(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    return path + (f"?{parsed.query}" if parsed.query else "")


def _status_text(result: CheckResult) -> str:
    if result.status is None:
        return "нет ответа"
    return f"HTTP {result.status}"


def _probable_reason(result: CheckResult) -> str:
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
    return "неизвестно."


def _recommended_action(result: CheckResult) -> str:
    if result.status is None:
        return "проверить доступность порта, nginx, backend-контейнер и сетевые таймауты."
    if result.status in {401, 403}:
        return "сверить ADMIN_API_TOKEN в GitHub Secrets и production .env, затем перезапустить deploy."
    if result.status == 404:
        return "проверить nginx location, router registration и актуальность URL в monitor."
    if result.status == 422:
        return "обновить payload monitor-запроса или backend-схему, чтобы контракт совпадал."
    if result.status >= 500:
        return "открыть backend logs за время прогона, проверить PostgreSQL readiness, долгие запросы и последние миграции."
    return "открыть лог workflow и ответ endpoint."


def _ok_summary(results: list[CheckResult]) -> list[str]:
    ok = [item for item in results if item.ok]
    slow = sorted(ok, key=lambda item: item.elapsed_ms, reverse=True)[:3]
    if not slow:
        return []
    return [f"• {item.spec.label}: HTTP {item.status}, {item.elapsed_ms} мс" for item in slow]


def failure_report(*, host: str, results: list[CheckResult]) -> str:
    failed = [item for item in results if not item.ok]
    lines = [
        "❌ CITY GO · API MONITOR",
        "Статус: найдены ошибки HTTP 4xx/5xx или сетевые сбои",
        f"Хост: {host}",
        f"Итог: {len(results) - len(failed)}/{len(results)} проверок успешно, {len(failed)} упало",
        "",
        "Сломанные проверки:",
    ]
    for index, item in enumerate(failed[:6], start=1):
        lines.extend(
            [
                f"{index}. {item.spec.label}",
                f"   Запрос: {item.spec.method} {_endpoint_path(item.url)}",
                f"   Факт: {_status_text(item)} за {item.elapsed_ms} мс",
                f"   Техническая ошибка: {item.error or 'HTTP status >= 400'}",
                f"   Вероятная причина: {_probable_reason(item)}",
                f"   Что делать: {_recommended_action(item)}",
                f"   Ответ: {_short_body(item.body)}",
            ]
        )
    if len(failed) > 6:
        lines.append(f"Ещё упавших проверок: {len(failed) - 6}")

    ok_summary = _ok_summary(results)
    if ok_summary:
        lines.extend(["", "Самые медленные успешные проверки:", *ok_summary])

    lines.extend(
        [
            "",
            "Следующий шаг: открыть GitHub run и backend logs за время прогона. При 500 сначала проверить /ready, PostgreSQL connections и последние миграции.",
            f"GitHub Actions: {_run_url()}",
        ]
    )
    return "\n".join(lines)


def success_report(*, host: str, results: list[CheckResult]) -> str:
    lines = [
        "✅ CITY GO · API MONITOR",
        "Статус: все API-проверки прошли",
        f"Хост: {host}",
        f"Итог: {len(results)}/{len(results)} проверок успешно",
    ]
    slow = _ok_summary(results)
    if slow:
        lines.extend(["Медленные успешные проверки:", *slow])
    lines.append(f"GitHub Actions: {_run_url()}")
    return "\n".join(lines)


def run_monitor(host: str, *, admin_token: str) -> tuple[int, str]:
    base_url = _base_url(host)
    results = [run_check(spec, base_url=base_url, admin_token=admin_token) for spec in default_checks()]
    failed = [item for item in results if not item.ok]
    if failed:
        return 1, failure_report(host=host, results=results)
    return 0, success_report(host=host, results=results)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("PROD_HOST", ""))
    parser.add_argument("--admin-token", default=os.getenv("ADMIN_API_TOKEN", ""))
    parser.add_argument("--notification-file", type=Path, required=True)
    args = parser.parse_args()

    if not args.host.strip():
        args.notification_file.write_text(
            "❌ CITY GO · API MONITOR\n"
            "Статус: проверка не запущена\n"
            "Проблема: GitHub secret SSH_HOST/PROD_HOST пустой.\n"
            "Что делать: заполнить secret SSH_HOST и повторить workflow.\n"
            f"GitHub Actions: {_run_url()}\n",
            encoding="utf-8",
        )
        return 1

    exit_code, text = run_monitor(args.host.strip(), admin_token=args.admin_token.strip())
    args.notification_file.write_text(text + "\n", encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
