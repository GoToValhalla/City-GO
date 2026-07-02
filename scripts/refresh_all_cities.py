#!/usr/bin/env python3
"""LEGACY/SCOPE REFRESH OPERATOR SCRIPT.

Status: historical production-container refresh script for enabled import scopes.

How it worked:
- Runs old OSM import v2 for enabled `CityImportScope` rows.
- Runs Data Coverage Assurance.
- Sends an operations report.

Current source of truth for admin-triggered imports:
- admin city import queue/job services;
- `CityAdminImportJob` and admin import runner;
- publication/product state repair scripts for publication state.

Rules:
- Do not use this script to repair publication state.
- Do not allow failures here to change `City.is_active` or `City.launch_status`.
- Keep only as an operator compatibility script until scope refresh is migrated to
  the current admin import job model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_

from data.scripts.import_city_osm_v2 import run as run_osm_import
from db.session import SessionLocal
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_image import PUBLIC_PLACE_IMAGE_STATUSES, PlaceImage
from services.data_coverage_assurance import run_data_coverage_assurance


@dataclass
class CityMetrics:
    slug: str
    name: str
    total: int = 0
    active: int = 0
    published: int = 0
    visible: int = 0
    route_eligible: int = 0
    searchable: int = 0
    with_address: int = 0
    with_photo: int = 0
    needs_publication_review: int = 0
    unverified: int = 0
    readiness_score: int = 0
    quality_status: str = "unknown"


@dataclass
class CityRun:
    slug: str
    name: str
    before: CityMetrics
    after: CityMetrics | None = None
    scopes: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    coverage_summary: dict[str, Any] | None = None
    coverage_acceptance: dict[str, Any] | None = None

    def add_scope_result(self, result: dict[str, Any]) -> None:
        self.scopes.append(result)
        assurance = result.get("data_coverage_assurance") if isinstance(result, dict) else None
        if isinstance(assurance, dict):
            summary = assurance.get("summary")
            acceptance = assurance.get("acceptance")
            if isinstance(summary, dict):
                self.coverage_summary = summary
            if isinstance(acceptance, dict):
                self.coverage_acceptance = acceptance

    @property
    def created(self) -> int:
        return _sum_scope_number(self.scopes, "created")

    @property
    def updated(self) -> int:
        return _sum_scope_number(self.scopes, "updated")

    @property
    def unchanged(self) -> int:
        return _sum_scope_number(self.scopes, "unchanged")

    @property
    def needs_review(self) -> int:
        return _sum_scope_number(self.scopes, "needs_review")

    @property
    def rejected(self) -> int:
        return _sum_scope_number(self.scopes, "rejected")

    @property
    def hidden(self) -> int:
        return _sum_scope_number(self.scopes, "hidden")

    @property
    def missing_from_source(self) -> int:
        return _sum_scope_number(self.scopes, "missing_from_source")


@dataclass
class RefreshReport:
    started_at: datetime
    finished_at: datetime
    dry_run: bool
    city_filter: str | None
    city_runs: list[CityRun]

    @property
    def failed_count(self) -> int:
        return sum(len(city.failures) for city in self.city_runs)

    @property
    def total_jobs(self) -> int:
        return sum(len(city.scopes) + len(city.failures) for city in self.city_runs)

    @property
    def created(self) -> int:
        return sum(city.created for city in self.city_runs)

    @property
    def updated(self) -> int:
        return sum(city.updated for city in self.city_runs)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh all enabled City GO city import scopes")
    parser.add_argument("--city", help="Refresh only one city slug")
    parser.add_argument("--apply", action="store_true", help="Write imported data to production DB")
    parser.add_argument("--dry-run", action="store_true", help="Fetch/normalize sources without DB changes")
    parser.add_argument("--sleep-seconds", type=float, default=5.0, help="Delay between scope imports")
    parser.add_argument("--send-telegram", action="store_true", help="Send Telegram notification")
    parser.add_argument("--no-telegram", action="store_true", help="Do not send Telegram notification")
    parser.add_argument("--allow-failures", action="store_true", help="Exit 0 even if some scopes failed")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.apply == args.dry_run:
        raise SystemExit("Choose exactly one of --apply or --dry-run")

    started_at = datetime.now(UTC)
    report: RefreshReport | None = None

    try:
        city_runs = run_refresh(
            city_slug=args.city,
            dry_run=args.dry_run,
            sleep_seconds=max(args.sleep_seconds, 0.0),
        )
        report = RefreshReport(
            started_at=started_at,
            finished_at=datetime.now(UTC),
            dry_run=args.dry_run,
            city_filter=args.city,
            city_runs=city_runs,
        )
        text = format_report(report)
        print(text)
        print("\n=== JSON SUMMARY ===")
        print(json.dumps(report_to_dict(report), ensure_ascii=False, indent=2, default=str))

        should_send = args.send_telegram and not args.no_telegram
        if should_send:
            send_telegram_chunks(text)

        if report.failed_count and not args.allow_failures:
            return 1
        return 0
    except BaseException as exc:  # noqa: BLE001 - operations script must notify about fatal failures.
        finished_at = datetime.now(UTC)
        text = format_fatal_report(
            started_at=started_at,
            finished_at=finished_at,
            dry_run=args.dry_run,
            city_filter=args.city,
            exc=exc,
        )
        print(text, file=sys.stderr)
        if args.send_telegram and not args.no_telegram:
            try:
                send_telegram_chunks(text)
            except Exception as notify_exc:  # noqa: BLE001
                print(f"telegram_notification_failed: {notify_exc}", file=sys.stderr)
        return 1


def run_refresh(*, city_slug: str | None, dry_run: bool, sleep_seconds: float) -> list[CityRun]:
    jobs = load_jobs(city_slug=city_slug)
    if not jobs:
        raise RuntimeError(f"No enabled import scopes found for city={city_slug or 'ALL'}")

    by_city: dict[str, CityRun] = {}
    for city, _scope in jobs:
        if city.slug not in by_city:
            by_city[city.slug] = CityRun(
                slug=city.slug,
                name=city.name,
                before=load_city_metrics(city.slug),
            )

    for index, (city, scope) in enumerate(jobs, start=1):
        label = f"{city.slug}/{scope.code}/{scope.import_profile}"
        print(f"\n=== [{index}/{len(jobs)}] refresh {label} ===", flush=True)
        mode = "--dry-run" if dry_run else "--apply"
        try:
            result = run_osm_import([
                "--city",
                city.slug,
                "--scope",
                scope.code,
                "--profile",
                scope.import_profile,
                mode,
            ])
            by_city[city.slug].add_scope_result(result)
            print(json.dumps(result, ensure_ascii=False, default=str)[:6000], flush=True)
        except BaseException as exc:  # noqa: BLE001 - keep refreshing other cities and report failures.
            failure = {"scope": scope.code, "profile": scope.import_profile, "error": str(exc)}
            by_city[city.slug].failures.append(failure)
            print(f"FAILED {label}: {exc}", flush=True)

        if sleep_seconds and index < len(jobs):
            time.sleep(sleep_seconds)

    if not dry_run:
        refresh_coverage_for_touched_cities(by_city)

    for city_run in by_city.values():
        city_run.after = load_city_metrics(city_run.slug)

    return list(by_city.values())


def load_jobs(*, city_slug: str | None) -> list[tuple[City, CityImportScope]]:
    with SessionLocal() as db:
        query = (
            db.query(City, CityImportScope)
            .join(CityImportScope, CityImportScope.city_id == City.id)
            .filter(CityImportScope.enabled.is_(True))
            .filter(CityImportScope.status != "paused")
            .filter(CityImportScope.bbox.isnot(None))
        )
        if city_slug:
            query = query.filter(City.slug == city_slug)
        rows = query.order_by(City.slug, CityImportScope.priority, CityImportScope.code).all()
        return [(city, scope) for city, scope in rows]


def refresh_coverage_for_touched_cities(city_runs: dict[str, CityRun]) -> None:
    for city_run in city_runs.values():
        try:
            with SessionLocal() as db:
                coverage = run_data_coverage_assurance(db, city_slug=city_run.slug)
                db.commit()
            summary = coverage.get("summary")
            acceptance = coverage.get("acceptance")
            if isinstance(summary, dict):
                city_run.coverage_summary = summary
            if isinstance(acceptance, dict):
                city_run.coverage_acceptance = acceptance
        except Exception as exc:  # noqa: BLE001
            city_run.failures.append({"scope": "data_coverage_assurance", "profile": "coverage", "error": str(exc)})


def load_city_metrics(city_slug: str) -> CityMetrics:
    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            raise RuntimeError(f"Unknown city: {city_slug}")

        base = db.query(Place).filter(Place.city_id == city.id)
        address_present = and_(Place.address.isnot(None), func.length(func.trim(Place.address)) > 0)
        image_url_present = and_(Place.image_url.isnot(None), func.length(func.trim(Place.image_url)) > 0)
        image_relation_present = Place.images.any(PlaceImage.status.in_(PUBLIC_PLACE_IMAGE_STATUSES))

        return CityMetrics(
            slug=city.slug,
            name=city.name,
            total=_count(base),
            active=_count(base.filter(Place.is_active.is_(True))),
            published=_count(base.filter(Place.is_published.is_(True))),
            visible=_count(base.filter(Place.is_visible_in_catalog.is_(True))),
            route_eligible=_count(base.filter(Place.is_route_eligible.is_(True))),
            searchable=_count(base.filter(Place.is_searchable.is_(True))),
            with_address=_count(base.filter(address_present)),
            with_photo=_count(base.filter(or_(image_url_present, image_relation_present))),
            needs_publication_review=_count(base.filter(Place.publication_status == "needs_review")),
            unverified=_count(base.filter(Place.verification_status != "verified")),
            readiness_score=int(city.readiness_score or 0),
            quality_status=city.quality_status or "unknown",
        )


def _count(query: Any) -> int:
    return int(query.with_entities(func.count(Place.id)).scalar() or 0)


def format_report(report: RefreshReport) -> str:
    status_icon = "✅" if report.failed_count == 0 else "⚠️"
    mode = "DRY RUN" if report.dry_run else "APPLY"
    lines = [
        f"{status_icon} CITY GO · ОБНОВЛЕНИЕ ГОРОДОВ",
        f"Статус: {'успешно' if report.failed_count == 0 else 'завершено с ошибками'}",
        f"Режим: {mode}",
        f"Фильтр: {report.city_filter or 'все города'}",
        f"Длительность: {_duration(report.started_at, report.finished_at)}",
        f"Задач импорта: {report.total_jobs}",
        f"Итого добавлено: {report.created}",
        f"Итого обновлено: {report.updated}",
    ]

    if report.failed_count:
        lines.append(f"Ошибок: {report.failed_count}")

    for city in report.city_runs:
        lines.extend(["", format_city_section(city, dry_run=report.dry_run)])

    if report.failed_count:
        lines.extend([
            "",
            "Что делать: открыть GitHub Actions → Refresh City Catalog → failed job, затем смотреть блок FAILED по scope.",
        ])
    else:
        lines.extend([
            "",
            "Что делать дальше: открыть админку → Покрытие/Верификация и подтвердить места из очереди проверки.",
        ])

    return "\n".join(lines)


def format_city_section(city: CityRun, *, dry_run: bool) -> str:
    after = city.after or city.before
    total_delta = after.total - city.before.total
    address_delta = after.with_address - city.before.with_address
    photo_delta = after.with_photo - city.before.with_photo
    coverage = city.coverage_summary or {}
    acceptance = city.coverage_acceptance or {}

    lines = [
        f"🏙 {city.name} ({city.slug})",
        f"Места: {city.before.total} → {after.total} ({_signed(total_delta)})",
        f"Добавлено: {city.created}; обновлено: {city.updated}; без изменений: {city.unchanged}",
        f"С адресами: {after.with_address}/{after.total} ({_pct(after.with_address, after.total)}, {_signed(address_delta)})",
        f"С фото: {after.with_photo}/{after.total} ({_pct(after.with_photo, after.total)}, {_signed(photo_delta)})",
        f"Опубликовано: {after.published}; видно в каталоге: {after.visible}; можно в маршруты: {after.route_eligible}",
        f"На публикационную проверку: {after.needs_publication_review}; непроверенных: {after.unverified}",
        f"Readiness: {after.readiness_score}% · {after.quality_status}",
    ]

    if coverage:
        lines.append(
            "Coverage: "
            f"matched={coverage.get('matched', 'n/a')}; "
            f"unresolved={coverage.get('unresolved', 'n/a')}; "
            f"critical={coverage.get('critical_unresolved', 'n/a')}"
        )
    if acceptance:
        accepted = acceptance.get("accepted")
        reason = acceptance.get("reason") or acceptance.get("status") or ""
        lines.append(f"Gate: {'accepted' if accepted else 'blocked'} {reason}".strip())

    if dry_run:
        raw_count = _sum_scope_number(city.scopes, "raw_count")
        rejected = _sum_scope_number(city.scopes, "rejected")
        lines.append(f"Dry run: найдено raw={raw_count}; отсеяно={rejected}; БД не менялась")
    else:
        lines.append(f"Отсеяно источником: {city.rejected}; скрыто: {city.hidden}; пропало из источника: {city.missing_from_source}")

    if city.failures:
        lines.append("Ошибки:")
        for failure in city.failures[:5]:
            lines.append(f"- {failure['scope']}/{failure['profile']}: {failure['error'][:240]}")
        if len(city.failures) > 5:
            lines.append(f"- ещё {len(city.failures) - 5} ошибок")

    return "\n".join(lines)


def format_fatal_report(*, started_at: datetime, finished_at: datetime, dry_run: bool, city_filter: str | None, exc: BaseException) -> str:
    return "\n".join([
        "❌ CITY GO · ОБНОВЛЕНИЕ ГОРОДОВ",
        "Статус: pipeline упал до завершения",
        f"Режим: {'DRY RUN' if dry_run else 'APPLY'}",
        f"Фильтр: {city_filter or 'все города'}",
        f"Длительность: {_duration(started_at, finished_at)}",
        f"Ошибка: {type(exc).__name__}: {exc}",
        "Что делать: открыть GitHub Actions → Refresh City Catalog → лог шага Refresh cities.",
    ])


def report_to_dict(report: RefreshReport) -> dict[str, Any]:
    return {
        "dry_run": report.dry_run,
        "city_filter": report.city_filter,
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "total_jobs": report.total_jobs,
        "failed_count": report.failed_count,
        "created": report.created,
        "updated": report.updated,
        "cities": [
            {
                "slug": city.slug,
                "name": city.name,
                "before": city.before.__dict__,
                "after": city.after.__dict__ if city.after else None,
                "created": city.created,
                "updated": city.updated,
                "unchanged": city.unchanged,
                "needs_review": city.needs_review,
                "rejected": city.rejected,
                "hidden": city.hidden,
                "missing_from_source": city.missing_from_source,
                "coverage_summary": city.coverage_summary,
                "coverage_acceptance": city.coverage_acceptance,
                "failures": city.failures,
            }
            for city in report.city_runs
        ],
    }


def send_telegram_chunks(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or os.getenv("BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN/BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    chunks = split_telegram_text(text)
    for index, chunk in enumerate(chunks, start=1):
        suffix = f"\n\n[{index}/{len(chunks)}]" if len(chunks) > 1 else ""
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": f"{chunk}{suffix}",
            "disable_web_page_preview": "true",
        }).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        if body.get("ok") is not True:
            raise RuntimeError(f"Telegram API rejected message: {body}")
        time.sleep(1)


def split_telegram_text(text: str, limit: int = 3600) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        addition = len(line) + 1
        if current and current_len + addition > limit:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += addition
    if current:
        chunks.append("\n".join(current))
    return chunks


def _sum_scope_number(scopes: list[dict[str, Any]], key: str) -> int:
    return sum(int(scope.get(key) or 0) for scope in scopes if isinstance(scope, dict))


def _signed(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def _pct(part: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{part / total * 100:.1f}%"


def _duration(started_at: datetime, finished_at: datetime) -> str:
    seconds = int((finished_at - started_at).total_seconds())
    minutes, rest = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}ч {minutes}м {rest}с"
    if minutes:
        return f"{minutes}м {rest}с"
    return f"{rest}с"


if __name__ == "__main__":
    raise SystemExit(main())
