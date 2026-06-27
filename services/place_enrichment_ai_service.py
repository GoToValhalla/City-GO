"""AI enrichment step for exported place enrichment batches."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from schemas.place_enrichment import EnrichmentAIRequest, EnrichmentAIResult
from services.admin_audit_service import write_admin_audit_log
from services.openai_client import request_json_object
from services.place_enrichment_batch.meta import read_batch_meta, update_batch_status
from services.place_enrichment_batch.paths import rel, resolve_batch_paths
from services.place_enrichment_csv import ALL_COLUMNS


DESCRIPTION_FIELD = "description"


def run_ai_batch_enrichment(
    db: Session,
    batch_id: str,
    req: EnrichmentAIRequest,
    actor: str,
) -> EnrichmentAIResult:
    meta = read_batch_meta(batch_id)
    if meta is None:
        raise FileNotFoundError(f"Batch not found: {batch_id}")

    paths, archived = resolve_batch_paths(batch_id)
    if archived:
        raise FileNotFoundError(f"Batch is archived and cannot be AI-enriched: {batch_id}")

    export_path = paths["export_csv"]
    if not export_path.exists():
        raise FileNotFoundError(f"export.csv missing for batch {batch_id}")

    rows = _read_rows(export_path)
    errors: list[str] = []
    rows_processed = 0
    rows_updated = 0
    requested_fields = {field.strip() for field in req.fields if field.strip()}

    if DESCRIPTION_FIELD not in requested_fields:
        errors.append("Only description AI enrichment is currently supported")
    else:
        for row in rows:
            if rows_processed >= req.limit:
                break
            if not _needs_description(row, force=req.force):
                continue
            rows_processed += 1
            payload = _generate_description(row)
            short_description = str(payload.get("short_description") or "").strip()
            if not short_description:
                errors.append(f"row {row.get('id') or '?'}: empty short_description")
                continue
            row["suggested_short_description"] = short_description[:500]
            row["suggested_data_source"] = "openai"
            row["suggested_confidence"] = _format_confidence(payload.get("confidence"))
            row["suggested_comment"] = str(payload.get("comment") or "AI-generated description").strip()[:500]
            rows_updated += 1

    enriched_path = paths["enriched_csv"]
    _write_rows(enriched_path, rows)
    update_batch_status(batch_id, "enriched", "preview_import")
    write_admin_audit_log(
        db,
        actor=actor,
        action="place_enrichment_ai_enrich",
        entity_type="place_enrichment_batch",
        entity_id=batch_id,
        new_value={
            "batch_id": batch_id,
            "model": settings.openai_model,
            "rows_processed": rows_processed,
            "rows_updated": rows_updated,
            "errors": errors,
        },
    )
    db.commit()
    result = EnrichmentAIResult(
        batch_id=batch_id,
        model=settings.openai_model,
        rows_processed=rows_processed,
        rows_updated=rows_updated,
        errors=errors,
        enriched_csv_path=rel(enriched_path),
    )
    _send_ai_enrichment_notice(result, city_slug=meta.city_slug)
    return result


def _read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=ALL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = {col: row.get(col, "") for col in ALL_COLUMNS}
            writer.writerow(normalized)


def _needs_description(row: dict[str, str], *, force: bool) -> bool:
    if force:
        return True
    current = (row.get("current_short_description") or "").strip()
    suggested = (row.get("suggested_short_description") or "").strip()
    return not current and not suggested


def _generate_description(row: dict[str, str]) -> dict[str, Any]:
    return request_json_object(
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты редактор туристического каталога City GO. Пиши только проверяемо и аккуратно. "
                    "Не выдумывай факты, цены, часы работы, рейтинги, события и услуги. "
                    "Ответ строго JSON object."
                ),
            },
            {
                "role": "user",
                "content": _build_user_prompt(row),
            },
        ],
        model=settings.openai_model,
        temperature=0.2,
    )


def _build_user_prompt(row: dict[str, str]) -> str:
    return (
        "Сгенерируй короткое описание места на русском для карточки туристического приложения.\n"
        "Нужно вернуть JSON с полями: short_description, confidence, comment.\n"
        "short_description: 1-2 предложения, до 500 символов, без рекламного тона.\n"
        "confidence: число от 0 до 1.\n"
        "comment: коротко объясни, на каких входных данных основан текст.\n\n"
        f"Название: {row.get('title') or ''}\n"
        f"Категория: {row.get('category') or ''}\n"
        f"Город: {row.get('city_name') or row.get('city_slug') or ''}\n"
        f"Адрес: {row.get('current_address') or ''}\n"
        f"Источник: {row.get('source') or ''}\n"
        f"URL источника: {row.get('source_url') or ''}\n"
        f"Текущее описание: {row.get('current_short_description') or ''}\n"
        f"Заметки: {row.get('notes') or ''}"
    )


def _format_confidence(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.5
    numeric = max(0.0, min(1.0, numeric))
    return f"{numeric:.2f}"


def _send_ai_enrichment_notice(result: EnrichmentAIResult, *, city_slug: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    status_icon = "✅" if not result.errors else "⚠️"
    text = (
        f"{status_icon} City GO · AI обогащение\n"
        f"Город: {city_slug}\n"
        f"Пакет: {result.batch_id}\n"
        f"Модель: {result.model}\n"
        f"Обработано: {result.rows_processed}\n"
        f"Подготовлено изменений: {result.rows_updated}\n"
        f"Ошибок: {len(result.errors)}\n"
        "Следующий шаг: открыть пакет в админке, проверить предпросмотр и применить."
    )
    try:
        httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=8,
        )
    except httpx.HTTPError:
        return