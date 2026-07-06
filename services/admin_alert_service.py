"""Runtime admin alerts for import/enrichment incidents."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from core.config import settings

_MAX_DETAILS_CHARS = 700

_STATUS_LABELS = {
    "needs_review": "нужна проверка",
    "not_ready": "не готово",
    "ready": "готово",
    "published": "опубликовано",
    "success": "успешно",
    "success_with_warnings": "завершено с предупреждениями",
    "partial_success": "частично завершено",
    "failed": "ошибка",
    "stalled": "зависло",
}

_SOURCE_LABELS = {
    "admin_city_enrichment": "обогащение данных",
    "admin_city_import": "импорт города",
}

_TITLE_LABELS = {
    "Enrichment pipeline finished": "Обогащение завершено",
    "Enrichment pipeline failed": "Ошибка обогащения",
    "Import pipeline finished": "Импорт завершён",
    "Import completed with warnings": "Импорт завершён с предупреждениями",
    "Import pipeline failed": "Ошибка импорта",
    "Import job stalled": "Задача импорта зависла",
    "Import worker job failed": "Ошибка import-worker",
}

_STEP_LABELS = {
    "collecting_places": "сбор мест",
    "finding_addresses": "поиск адресов",
    "finding_images": "поиск фотографий",
    "source_enrichment": "обогащение внешними источниками",
    "enrich_external_sources": "обогащение внешними источниками",
    "generate_ai_descriptions": "подготовка описаний",
    "fetch_photo_candidates": "поиск фотографий",
    "unified_pipeline": "единый pipeline",
}


def send_admin_alert(
    *,
    title: str,
    message: str,
    level: str = "error",
    city_slug: str | None = None,
    job_id: int | None = None,
    details: dict[str, Any] | None = None,
    chat_id_override: str | None = None,
) -> dict[str, object]:
    """Send a best-effort Telegram alert without breaking background jobs."""
    token = settings.telegram_bot_token or settings.bot_token
    chat_id = chat_id_override or settings.telegram_chat_id
    if not token or not chat_id:
        print(
            "admin_alert_not_configured: set TELEGRAM_CHAT_ID and "
            f"TELEGRAM_BOT_TOKEN or BOT_TOKEN to receive '{title}' alerts"
        )
        return {"sent": False, "reason": "not_configured"}

    text = _format_alert_text(
        title=title,
        message=message,
        level=level,
        city_slug=city_slug,
        job_id=job_id,
        details=details,
    )
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:  # noqa: S310
            response.read()
        return {"sent": True}
    except Exception as exc:  # noqa: BLE001
        print(f"admin_alert_send_failed: {exc}")
        return {"sent": False, "reason": str(exc)[:300]}


def _format_alert_text(
    *,
    title: str,
    message: str,
    level: str,
    city_slug: str | None,
    job_id: int | None,
    details: dict[str, Any] | None,
) -> str:
    prefix = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(level, "⚠️")
    lines = [f"{prefix} City GO: {_title_label(title)}"]
    human_message = _human_message(title, message)
    if human_message:
        lines.append(human_message)
    if city_slug:
        lines.append(f"Город: {city_slug}")
    if job_id is not None:
        lines.append(f"Job: {job_id}")
    lines.append(f"Время: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    summary = _format_details_summary(title, details or {})
    if summary:
        lines.append("")
        lines.extend(summary)
    return "\n".join(lines)


def _title_label(title: str) -> str:
    return _TITLE_LABELS.get(title, title)


def _human_message(title: str, message: str) -> str:
    if title == "Enrichment pipeline finished":
        return "Город прошел обогащение и ждет ручной проверки."
    if title == "Import job stalled":
        return "Worker не обновлял прогресс дольше порога. Задача остановлена watchdog."
    return message.strip()


def _format_details_summary(title: str, details: dict[str, Any]) -> list[str]:
    if title == "Enrichment pipeline finished":
        return _format_enrichment_finished(details)
    if title in {"Import pipeline finished", "Import completed with warnings"}:
        return _format_import_finished(details)
    if title == "Import job stalled":
        return _format_stalled_job(details)
    if title in {"Enrichment pipeline failed", "Import pipeline failed"}:
        return _format_failed_job(details)
    return _format_compact_details(details)


def _format_import_finished(details: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    status = _status_label(details.get("status"))
    source = _source_label(details.get("source"))
    places_total = details.get("places_total")
    if status:
        lines.append(f"Статус: {status}")
    if source:
        lines.append(f"Тип задачи: {source}")
    if places_total is not None:
        lines.append(f"Мест в городе: {places_total}")

    warnings = details.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("Предупреждения:")
        for warning in warnings[:5]:
            if not isinstance(warning, dict):
                continue
            step = str(warning.get("step") or "неизвестный этап")
            error = str(warning.get("error") or "причина не указана")
            if len(error) > 240:
                error = error[:240] + "…"
            lines.append(f"• {_STEP_LABELS.get(step, step)}: {error}")
        if len(warnings) > 5:
            lines.append(f"• Ещё предупреждений: {len(warnings) - 5}")
        lines.append("Что дальше: открыть задачу импорта и повторить только проблемные шаги.")
    else:
        readiness = details.get("readiness") if isinstance(details.get("readiness"), dict) else {}
        score = readiness.get("readiness_score")
        if score is not None:
            lines.append(f"Готовность города: {score}/100")
        lines.append("Что дальше: проверить качество данных и опубликовать город.")
    return lines


def _format_enrichment_finished(details: dict[str, Any]) -> list[str]:
    readiness = details.get("readiness") if isinstance(details.get("readiness"), dict) else {}
    components = readiness.get("components") if isinstance(readiness.get("components"), dict) else {}
    score = readiness.get("readiness_score")
    status = _status_label(readiness.get("status"))
    places_total = _first_number(components.get("places_total"), details.get("places_total"))
    places_active = components.get("places_active")
    eligible_places = components.get("eligible_places")

    lines = [f"Итог: readiness {score}/100, статус: {status}" if score is not None else f"Итог: статус: {status}"]
    place_bits = []
    if places_total is not None:
        place_bits.append(f"всего {places_total}")
    if places_active is not None:
        place_bits.append(f"активных {places_active}")
    if eligible_places is not None:
        place_bits.append(f"для маршрутов {eligible_places}")
    if place_bits:
        lines.append("Места: " + ", ".join(place_bits))

    coverage = [
        ("адреса", components.get("address_coverage_pct")),
        ("фото", components.get("photo_coverage_pct")),
        ("описания", components.get("description_coverage_pct")),
        ("часы", components.get("hours_any_pct")),
        ("маршруты", components.get("route_eligibility_pct")),
        ("верификация", components.get("verification_coverage_pct")),
    ]
    coverage_text = [f"{label} {_pct(value)}" for label, value in coverage if value is not None]
    if coverage_text:
        lines.append("Покрытие: " + ", ".join(coverage_text))
    next_steps = _enrichment_next_steps(components)
    if next_steps:
        lines.append("Что дальше: " + next_steps)
    return lines


def _enrichment_next_steps(components: dict[str, Any]) -> str:
    weak: list[str] = []
    if _as_float(components.get("photo_coverage_pct")) < 60:
        weak.append("добавить фото")
    if _as_float(components.get("verification_coverage_pct")) < 80:
        weak.append("проверить места")
    if _as_float(components.get("hours_any_pct")) < 50:
        weak.append("добить часы работы")
    if weak:
        return ", ".join(weak) + "."
    return "посмотреть качество данных и публиковать, если всё в порядке."


def _format_stalled_job(details: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    source = _source_label(details.get("source"))
    if source:
        lines.append(f"Тип задачи: {source}")
    last_error = details.get("last_error")
    if last_error:
        lines.append(f"Причина: {last_error}")
    lines.append("Что дальше: после деплоя исправления нажать «Повторить» для этого города.")
    return lines


def _format_failed_job(details: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    source = _source_label(details.get("source"))
    if source:
        lines.append(f"Тип задачи: {source}")
    status = _status_label(details.get("status"))
    if status:
        lines.append(f"Статус: {status}")
    step_details = details.get("step_details")
    if isinstance(step_details, dict) and step_details.get("error"):
        lines.append(f"Ошибка: {step_details['error']}")
    warnings = details.get("warnings")
    if isinstance(warnings, list):
        lines.extend(_format_import_finished({"warnings": warnings})[1:])
    return lines


def _format_compact_details(details: dict[str, Any]) -> list[str]:
    if not details:
        return []
    lines: list[str] = []
    for key in ("status", "source", "places_total", "last_error"):
        value = details.get(key)
        if value is None:
            continue
        if key == "source":
            value = _source_label(value) or value
        elif key == "status":
            value = _status_label(value)
        lines.append(f"{key}: {value}")
    if lines:
        return lines
    compact = json.dumps(details, ensure_ascii=False, default=str)
    if len(compact) > _MAX_DETAILS_CHARS:
        compact = compact[:_MAX_DETAILS_CHARS] + "…"
    return [f"Тех. детали: {compact}"]


def _status_label(value: object) -> str:
    text = str(value or "unknown")
    return _STATUS_LABELS.get(text, text)


def _source_label(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return _SOURCE_LABELS.get(text, text)


def _pct(value: object) -> str:
    number = _as_float(value)
    if number.is_integer():
        return f"{int(number)}%"
    return f"{number:.1f}%"


def _as_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _first_number(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None
