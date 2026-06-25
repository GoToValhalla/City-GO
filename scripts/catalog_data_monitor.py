#!/usr/bin/env python3
"""Validate public catalog availability and build a readable Telegram report."""
from __future__ import annotations

import argparse
import json
import os
import sys
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


def _short_body(body: str, limit: int = 700) -> str:
    compact = " ".join((body or "").replace("\r", " ").split())
    if not compact:
        return "пустой ответ"
    return compact[:limit] + ("…" if len(compact) > limit else "")


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


def failure_report(*, title: str, host: str, result: HttpResult | None, problem: str, meaning: str, action: str) -> str:
    lines = [
        "❌ City GO · Каталог недоступен",
        "Проверка: публичный список городов и мест",
        f"Хост: {host}",
        f"Проблема: {problem}",
    ]
    if result is not None:
        path = urllib.parse.urlsplit(result.url).path
        query = urllib.parse.urlsplit(result.url).query
        endpoint = path + (f"?{query}" if query else "")
        lines.extend(
            [
                f"Endpoint: {result.method} {endpoint}",
                f"HTTP: {result.status if result.status is not None else 'нет ответа'}",
                f"Время ответа: {result.elapsed_ms} мс",
                f"Content-Type: {result.content_type or 'не указан'}",
                f"Ответ: {_short_body(result.body)}",
            ]
        )
    lines.extend(
        [
            f"Что это значит: {meaning}",
            f"Что делать: {action}",
            f"Run: {_run_url()}",
        ]
    )
    return "\n".join(lines)


def success_report(*, host: str, city_count: int, city_slug: str, places_total: int) -> str:
    return "\n".join(
        [
            "✅ City GO · Каталог доступен",
            f"Хост: {host}",
            f"Городов в выдаче: {city_count}",
            f"Проверенный город: {city_slug}",
            f"Мест в каталоге: {places_total}",
            f"Run: {_run_url()}",
        ]
    )


def run_monitor(host: str) -> tuple[int, str]:
    base_url = _base_url(host)
    cities = http_get(f"{base_url}/api/cities/available?include_draft=true")
    cities_payload, cities_error = parse_json(cities)
    if cities_error:
        return 1, failure_report(
            title="catalog_cities_failed",
            host=host,
            result=cities,
            problem=f"не удалось получить список городов: {cities_error}",
            meaning="публичный каталог не может выбрать город; пользователь увидит пустой список или зависание.",
            action="проверить backend, nginx proxy и /api/cities/available; открыть логи backend за время прогона.",
        )

    city_count = _items_count(cities_payload)
    if city_count < 1:
        return 1, failure_report(
            title="catalog_cities_empty",
            host=host,
            result=cities,
            problem="API вернул 0 доступных городов",
            meaning="HTTP может быть 200, но витрина фактически пустая; часто причина в статусах городов или feature flags.",
            action="проверить is_active/launch_status городов и флаги видимости web_app_enabled/city_visible_to_users.",
        )

    city_slug = _first_city_slug(cities_payload)
    if not city_slug:
        return 1, failure_report(
            title="catalog_city_slug_missing",
            host=host,
            result=cities,
            problem="первый город в ответе не содержит slug",
            meaning="frontend не сможет загрузить места для выбранного города.",
            action="проверить контракт /api/cities/available и данные таблицы cities.",
        )

    places_url = f"{base_url}/api/places?city_slug={urllib.parse.quote(city_slug)}&limit=1&offset=0"
    places = http_get(places_url)
    places_payload, places_error = parse_json(places)
    if places_error:
        return 1, failure_report(
            title="catalog_places_failed",
            host=host,
            result=places,
            problem=f"не удалось получить места для города {city_slug}: {places_error}",
            meaning="город есть, но каталог мест не открывается; вероятна ошибка запроса к БД или API places.",
            action="открыть backend logs по /api/places и проверить public visibility мест выбранного города.",
        )

    places_total = 0
    if isinstance(places_payload, dict):
        try:
            places_total = int(places_payload.get("total") or 0)
        except (TypeError, ValueError):
            places_total = 0
    if places_total < 1:
        return 1, failure_report(
            title="catalog_places_empty",
            host=host,
            result=places,
            problem=f"город {city_slug} есть, но видимых мест 0",
            meaning="frontend покажет пустой каталог; чаще всего места скрыты, сняты с публикации или не проходят route/catalog visibility.",
            action="проверить статусы мест, visible_in_catalog, city_id, review_required и последние импорты по этому городу.",
        )

    return 0, success_report(host=host, city_count=city_count, city_slug=city_slug, places_total=places_total)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("PROD_HOST", ""))
    parser.add_argument("--notification-file", type=Path, required=True)
    args = parser.parse_args()

    if not args.host.strip():
        args.notification_file.write_text(
            "❌ City GO · Каталог не проверен\nПроблема: GitHub secret SSH_HOST/PROD_HOST пустой.\nЧто делать: заполнить secret SSH_HOST и повторить workflow.\n"
            f"Run: {_run_url()}\n",
            encoding="utf-8",
        )
        return 1

    exit_code, text = run_monitor(args.host.strip())
    args.notification_file.write_text(text + "\n", encoding="utf-8")
    print(text)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
