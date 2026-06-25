#!/usr/bin/env python3
"""Validate public catalog availability and build a readable Telegram report."""
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
class HttpResult:
    method: str
    url: str
    status: int | None
    elapsed_ms: int
    body: str
    content_type: str
    error: str | None = None


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


def _looks_like_html(result: HttpResult | None) -> bool:
    if result is None:
        return False
    content_type = result.content_type.lower()
    body = (result.body or "").lstrip().lower()
    return "text/html" in content_type or body.startswith("<!doctype html") or body.startswith("<html")


def _looks_like_citygo_spa(result: HttpResult | None) -> bool:
    if not _looks_like_html(result):
        return False
    body = (result.body or "").lower()
    return "<title>city go</title>" in body or "/assets/index-" in body


def _response_excerpt(result: HttpResult) -> str:
    if _looks_like_citygo_spa(result):
        return "HTML frontend index.html City GO вместо JSON API. Полный HTML скрыт из уведомления."
    return _short_body(result.body)


def _endpoint(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path or "/"
    return path + (f"?{parsed.query}" if parsed.query else "")


def _status_text(result: HttpResult) -> str:
    if result.status is None:
        return "нет ответа"
    return f"HTTP {result.status}"


def _status_code_text(result: HttpResult) -> str:
    if result.status is None:
        return "нет ответа"
    return str(result.status)


def http_get(url: str, *, timeout: int = 25) -> HttpResult:
    started = time.monotonic()
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - production monitor URL from secrets
            body = response.read().decode("utf-8", errors="replace")
            return HttpResult(
                method="GET",
                url=url,
                status=int(response.status),
                elapsed_ms=int((time.monotonic() - started) * 1000),
                body=body,
                content_type=response.headers.get("content-type", ""),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return HttpResult(
            method="GET",
            url=url,
            status=int(exc.code),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            body=body,
            content_type=exc.headers.get("content-type", "") if exc.headers else "",
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - monitor must report any network/runtime failure
        return HttpResult(
            method="GET",
            url=url,
            status=None,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            body="",
            content_type="",
            error=str(exc),
        )


def parse_json(result: HttpResult) -> tuple[Any | None, str | None]:
    if result.status is None:
        return None, result.error or "запрос не выполнен"
    if result.status >= 400:
        return None, f"HTTP {result.status}"
    if _looks_like_citygo_spa(result):
        return None, "endpoint вернул frontend index.html вместо JSON API"
    if _looks_like_html(result):
        return None, "endpoint вернул HTML вместо JSON API"
    try:
        return json.loads(result.body), None
    except json.JSONDecodeError as exc:
        return None, f"ответ не является JSON: {exc.msg}"


def _items_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return len(items)
    return 0


def _first_city_slug(payload: Any) -> str | None:
    first: Any | None = None
    if isinstance(payload, list) and payload:
        first = payload[0]
    elif isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list) and items:
            first = items[0]
    if isinstance(first, dict):
        slug = first.get("slug")
        return str(slug) if slug else None
    return None


def _technical_error(result: HttpResult | None) -> str:
    if result is None:
        return "проверка остановилась до HTTP-запроса"
    if _looks_like_citygo_spa(result):
        return "ожидали JSON API, но получили frontend index.html"
    if _looks_like_html(result):
        return "ожидали JSON API, но получили HTML"
    if result.error:
        return result.error
    if result.status is None:
        return "нет HTTP-ответа"
    if result.status >= 400:
        return f"HTTP {result.status}"
    return "семантическая проверка данных не прошла"


def failure_report(
    *,
    host: str,
    result: HttpResult | None,
    problem: str,
    meaning: str,
    action: str,
    title: str | None = None,
) -> str:
    lines = [
        "❌ City GO · Каталог недоступен",
        "Статус: публичный каталог не прошёл проверку",
        "Сценарий: пользователь открывает город и список мест",
        f"Хост: {host}",
        f"Проблема: {problem}",
    ]
    if title:
        lines.append(f"Код проверки: {title}")
    if result is not None:
        lines.extend(
            [
                f"Endpoint: {result.method} {_endpoint(result.url)}",
                f"HTTP: {_status_code_text(result)}",
                f"Время: {result.elapsed_ms} мс",
                f"Content-Type: {result.content_type or 'не указан'}",
                f"Техническая причина: {_technical_error(result)}",
                f"Ответ: {_response_excerpt(result)}",
            ]
        )
    lines.extend(
        [
            f"Что это значит: {meaning}",
            f"Что делать: {action}",
            f"GitHub Actions: {_run_url()}",
        ]
    )
    return "\n".join(lines)


def success_report(*, host: str, city_count: int, city_slug: str, places_total: int) -> str:
    return "\n".join(
        [
            "✅ CITY GO · CATALOG DATA MONITOR",
            "Статус: публичный каталог доступен",
            f"Хост: {host}",
            f"Городов в выдаче: {city_count}",
            f"Проверенный город: {city_slug}",
            f"Мест в каталоге: {places_total}",
            f"GitHub Actions: {_run_url()}",
        ]
    )


def _html_api_failure(*, host: str, result: HttpResult, endpoint_name: str) -> tuple[int, str]:
    return 1, failure_report(
        host=host,
        result=result,
        problem=f"{endpoint_name} вернул frontend HTML вместо JSON",
        meaning="запрос не дошёл до нужного backend API или был перенаправлен на SPA. Это проблема routing/URL/trailing slash/nginx, а не доказательство пустой БД.",
        action="проверить API URL в monitor и frontend, trailing slash у backend route, nginx location /api/ и redirect FastAPI. Для places monitor должен использовать /api/places/.",
    )


def run_monitor(host: str) -> tuple[int, str]:
    base_url = _base_url(host)
    cities = http_get(f"{base_url}/api/cities/available?include_draft=true")
    cities_payload, cities_error = parse_json(cities)
    if cities_error:
        if _looks_like_html(cities):
            return _html_api_failure(host=host, result=cities, endpoint_name="список городов")
        return 1, failure_report(
            host=host,
            result=cities,
            problem=f"не удалось получить список городов: {cities_error}",
            meaning="публичная витрина не может выбрать город; пользователь увидит пустой селектор или зависание.",
            action="проверить backend/nginx для /api/cities/available, затем открыть backend logs за время прогона.",
        )

    city_count = _items_count(cities_payload)
    if city_count < 1:
        return 1, failure_report(
            host=host,
            result=cities,
            problem="API вернул 0 доступных городов",
            meaning="HTTP 200 не означает рабочий каталог: витрина фактически пустая. Частая причина — все города inactive/review_required или выключены feature flags.",
            action="проверить cities.is_active, launch_status, web_app_enabled, city_visible_to_users и последние импорты/миграции.",
        )

    city_slug = _first_city_slug(cities_payload)
    if not city_slug:
        return 1, failure_report(
            host=host,
            result=cities,
            problem="первый город в ответе не содержит slug",
            meaning="frontend не сможет загрузить места для выбранного города.",
            action="проверить контракт /api/cities/available и данные таблицы cities.",
        )

    # Trailing slash is intentional. Without it FastAPI can redirect /places to /places/;
    # through nginx that redirect may escape /api and return the frontend SPA HTML.
    places_url = f"{base_url}/api/places/?city_slug={urllib.parse.quote(city_slug)}&limit=1&offset=0"
    places = http_get(places_url)
    places_payload, places_error = parse_json(places)
    if places_error:
        if _looks_like_html(places):
            return _html_api_failure(host=host, result=places, endpoint_name=f"список мест для города {city_slug}")
        return 1, failure_report(
            host=host,
            result=places,
            problem=f"не удалось получить места для города {city_slug}: {places_error}",
            meaning="город есть, но список мест не открывается; вероятна ошибка API places, БД или visibility-фильтров.",
            action="открыть backend logs по /api/places/ и проверить public visibility мест выбранного города.",
        )

    places_total = 0
    if isinstance(places_payload, dict):
        try:
            places_total = int(places_payload.get("total") or 0)
        except (TypeError, ValueError):
            places_total = 0
    if places_total < 1:
        return 1, failure_report(
            host=host,
            result=places,
            problem=f"город {city_slug} есть, но видимых мест 0",
            meaning="frontend покажет пустой каталог; чаще всего места скрыты, сняты с публикации или не проходят catalog visibility.",
            action="проверить статусы places, visible_in_catalog, city_id, review_required и последние импорты по этому городу.",
        )

    return 0, success_report(host=host, city_count=city_count, city_slug=city_slug, places_total=places_total)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("PROD_HOST", ""))
    parser.add_argument("--notification-file", type=Path, required=True)
    args = parser.parse_args()

    if not args.host.strip():
        args.notification_file.write_text(
            "❌ CITY GO · CATALOG DATA MONITOR\n"
            "Статус: проверка не запущена\n"
            "Проблема: GitHub secret SSH_HOST/PROD_HOST пустой.\n"
            "Что делать: заполнить secret SSH_HOST и повторить workflow.\n"
            f"GitHub Actions: {_run_url()}\n",
            encoding="utf-8",
        )
        return 1

    exit_code, text = run_monitor(args.host.strip())
    args.notification_file.write_text(text + "\n", encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
