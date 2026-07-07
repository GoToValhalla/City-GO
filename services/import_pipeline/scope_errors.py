"""Classify import scope failures for admin diagnostics."""

from __future__ import annotations

from typing import Any


def classify_scope_error(error: str) -> dict[str, object]:
    text = str(error or "").lower()
    if "foreignkeyviolation" in text or "review_queue_items_job_id_fkey" in text:
        return {"kind": "data_integrity", "retryable": False, "admin_hint": "Ошибка связи review queue с import job. Повторите сбор после деплоя фикса."}
    if "reviewqueuejoblinkerror" in text or "invalid review_queue_items.job_id" in text:
        return {"kind": "data_integrity", "retryable": False, "admin_hint": "Передан неверный import job id. Повторите сбор города."}
    if "temporary failure in name resolution" in text or "urlopen error" in text or "timed out" in text or "name or service not known" in text:
        return {"kind": "source_failure", "retryable": True, "admin_hint": "Внешний источник OSM временно недоступен. Повторите сбор позже."}
    if "too many osm objects" in text:
        return {"kind": "source_limits", "retryable": False, "admin_hint": "Слишком много объектов OSM для scope. Сузьте bbox или профиль."}
    return {"kind": "scope_failure", "retryable": True, "admin_hint": "Scope завершился с ошибкой. Откройте детали и повторите сбор."}


def scope_failure_rows(results: list[dict[str, Any]] | None) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in results or []:
        if not isinstance(item, dict) or item.get("status") == "success":
            continue
        error = str(item.get("error") or item.get("reason") or item.get("status") or "unknown")
        meta = classify_scope_error(error)
        rows.append({"scope": item.get("scope"), "profile": item.get("profile"), "error": error[:1000], **meta})
    return rows


def import_failure_diagnostics(summary: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(summary, dict):
        return None
    scope_errors = summary.get("scope_errors")
    if not isinstance(scope_errors, list) or not scope_errors:
        return None
    kinds = sorted({str(row.get("kind") or "scope_failure") for row in scope_errors if isinstance(row, dict)})
    return {"scope_errors": scope_errors, "error_kinds": kinds, "primary_kind": kinds[0] if len(kinds) == 1 else "mixed"}
