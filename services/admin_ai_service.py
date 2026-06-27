"""One-click admin AI actions that hide technical enrichment steps from the UI."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from models.city import City
from models.place import Place
from schemas.admin_ai import (
    AdminAIModelOption,
    AdminAIResultItem,
    AdminAIRunRequest,
    AdminAIRunResult,
    AdminAITaskOption,
    AdminAITasksResponse,
)
from schemas.place_enrichment import EnrichmentAIRequest, PlaceEnrichmentExportRequest
from services.admin_audit_service import write_admin_audit_log
from services.openai_client import OpenAIClientError, request_json_object
from services.place_enrichment_ai_service import run_ai_batch_enrichment
from services.place_enrichment_import_service import run_import_apply, run_import_preview
from services.place_enrichment_service import run_enrichment_export
from services.telegram_notifications import send_telegram_notification

FILL_DESCRIPTIONS = "fill_descriptions"
FIND_NON_TOURIST = "find_non_tourist"

_TASKS = [
    AdminAITaskOption(
        id=FILL_DESCRIPTIONS,
        label="Заполнить описания мест",
        description="Найдёт места без описания, сгенерирует короткий текст и применит безопасные изменения автоматически.",
        result_mode="auto_apply",
        risk_level="safe",
    ),
    AdminAITaskOption(
        id=FIND_NON_TOURIST,
        label="Найти мусорные места",
        description="Проверит места и покажет подозрительные аптеки, банки, остановки и сервисные объекты без автоскрытия.",
        result_mode="review_report",
        risk_level="review",
    ),
]


def list_admin_ai_tasks() -> AdminAITasksResponse:
    return AdminAITasksResponse(
        tasks=_TASKS,
        model_options=[
            AdminAIModelOption(
                value="economy",
                label="Экономно",
                model=settings.openai_model,
                description="Дешевле и быстрее для массовых описаний.",
            ),
            AdminAIModelOption(
                value="quality",
                label="Качественно",
                model=settings.openai_quality_model,
                description="Лучше для проверки качества и спорных мест.",
            ),
        ],
        default_task_id=FILL_DESCRIPTIONS,
        default_model_mode="economy",
    )


def run_admin_ai_task(db: Session, req: AdminAIRunRequest, *, actor: str) -> AdminAIRunResult:
    city = db.query(City).filter(City.slug == req.city_slug).first()
    if city is None:
        raise ValueError("Город не найден")
    model = _model_for_mode(req.model_mode)
    if req.task_id == FILL_DESCRIPTIONS:
        result = _run_fill_descriptions(db, req, city=city, actor=actor, model=model)
    elif req.task_id == FIND_NON_TOURIST:
        result = _run_find_non_tourist(db, req, city=city, actor=actor, model=model)
    else:
        raise ValueError("AI-задача не поддерживается")
    _send_result_notice(result)
    return result


def _run_fill_descriptions(
    db: Session,
    req: AdminAIRunRequest,
    *,
    city: City,
    actor: str,
    model: str,
) -> AdminAIRunResult:
    export = run_enrichment_export(
        db,
        PlaceEnrichmentExportRequest(
            city_slug=city.slug,
            limit=req.limit,
            only_published=True,
            only_route_eligible=False,
            missing_fields=["description"],
            git_artifact=True,
        ),
        actor=actor,
    )
    batch_id = export.batch_id or export.export_id
    if export.total_exported <= 0 or not batch_id:
        result = AdminAIRunResult(
            task_id=FILL_DESCRIPTIONS,
            task_label="Заполнить описания мест",
            city_slug=city.slug,
            model=model,
            status="completed",
            rows_processed=0,
            rows_updated=0,
            applied=False,
            batch_id=batch_id,
            message="В выбранном городе не найдено опубликованных мест без описания.",
            next_action="Ничего делать не нужно.",
        )
        _audit_result(db, result, actor=actor)
        return result

    ai_result = run_ai_batch_enrichment(
        db,
        batch_id,
        EnrichmentAIRequest(limit=req.limit, force=False, fields=["description"], model=model),
        actor=actor,
        notify=False,
    )
    preview = run_import_preview(db, batch_id)
    if req.apply_safe_changes:
        apply = run_import_apply(db, batch_id, actor=actor)
        rows_updated = apply.rows_updated
        applied = True
        message = f"AI подготовил и применил описания: {rows_updated} мест."
        next_action = "Откройте список мест города и проверьте обновлённые карточки."
        errors = [*ai_result.errors, *preview.errors, *apply.errors]
    else:
        rows_updated = preview.rows_with_changes
        applied = False
        message = f"AI подготовил описания: {rows_updated} мест. Изменения ждут проверки."
        next_action = "Откройте пакет в низкоуровневом разделе обогащения и примените изменения."
        errors = [*ai_result.errors, *preview.errors]

    result = AdminAIRunResult(
        task_id=FILL_DESCRIPTIONS,
        task_label="Заполнить описания мест",
        city_slug=city.slug,
        model=model,
        status="completed" if not errors else "completed_with_warnings",
        rows_processed=ai_result.rows_processed,
        rows_updated=rows_updated,
        applied=applied,
        batch_id=batch_id,
        errors=errors,
        message=message,
        next_action=next_action,
    )
    _audit_result(db, result, actor=actor)
    return result


def _run_find_non_tourist(
    db: Session,
    req: AdminAIRunRequest,
    *,
    city: City,
    actor: str,
    model: str,
) -> AdminAIRunResult:
    places = (
        db.query(Place)
        .filter(Place.city_id == city.id)
        .filter(Place.is_published.is_(True))
        .order_by(Place.id.desc())
        .limit(req.limit)
        .all()
    )
    if not places:
        places = (
            db.query(Place)
            .filter(Place.city_id == city.id)
            .order_by(Place.id.desc())
            .limit(req.limit)
            .all()
        )

    items: list[AdminAIResultItem] = []
    errors: list[str] = []
    for place in places:
        try:
            payload = _classify_non_tourist(place, city=city, model=model)
        except OpenAIClientError:
            raise
        except Exception as exc:  # noqa: BLE001 - one bad row should not kill the whole report
            errors.append(f"place {place.id}: {exc}")
            continue
        confidence = _confidence(payload.get("confidence"))
        is_problem = bool(payload.get("is_problem")) and confidence >= 0.55
        if not is_problem:
            continue
        items.append(AdminAIResultItem(
            place_id=place.id,
            title=place.title,
            summary=str(payload.get("reason") or "Подозрительное место для туристического каталога")[:500],
            recommended_action=str(payload.get("recommended_action") or "Проверить вручную")[:300],
            confidence=confidence,
        ))

    result = AdminAIRunResult(
        task_id=FIND_NON_TOURIST,
        task_label="Найти мусорные места",
        city_slug=city.slug,
        model=model,
        status="completed" if not errors else "completed_with_warnings",
        rows_processed=len(places),
        rows_updated=0,
        applied=False,
        items=items,
        errors=errors,
        message=f"AI проверил мест: {len(places)}. Подозрительных: {len(items)}.",
        next_action="Откройте найденные места и вручную исключите их из маршрутов или каталога.",
    )
    _audit_result(db, result, actor=actor)
    return result


def _classify_non_tourist(place: Place, *, city: City, model: str) -> dict[str, Any]:
    return request_json_object(
        model=model,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты модератор туристического каталога City GO. Определи, является ли место мусорным "
                    "для туристического маршрута: аптека, банк, банкомат, остановка, парковка, сервис, бытовая точка. "
                    "Не помечай музеи, парки, памятники, соборы, кафе, рестораны, пляжи и прогулочные места. "
                    "Ответ строго JSON object."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Верни JSON с полями: is_problem, confidence, reason, recommended_action.\n"
                    f"Город: {city.name} ({city.slug})\n"
                    f"Название: {place.title}\n"
                    f"Категория: {place.category or ''}\n"
                    f"Canonical category: {place.canonical_category or ''}\n"
                    f"Адрес: {place.address or ''}\n"
                    f"Описание: {place.short_description or ''}\n"
                    f"Источник: {place.source or ''}\n"
                    f"Route eligible: {place.is_route_eligible}"
                ),
            },
        ],
    )


def _model_for_mode(mode: str) -> str:
    if mode == "quality":
        return settings.openai_quality_model
    return settings.openai_model


def _confidence(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.5
    return max(0.0, min(1.0, numeric))


def _audit_result(db: Session, result: AdminAIRunResult, *, actor: str) -> None:
    write_admin_audit_log(
        db,
        actor=actor,
        action="admin_ai_run",
        entity_type="admin_ai_task",
        entity_id=result.task_id,
        new_value=result.model_dump(),
    )
    db.commit()


def _send_result_notice(result: AdminAIRunResult) -> None:
    status_icon = "✅" if result.status == "completed" else "⚠️"
    send_telegram_notification(
        f"{status_icon} City GO · AI\n"
        f"Задача: {result.task_label}\n"
        f"Город: {result.city_slug}\n"
        f"Модель: {result.model}\n"
        f"Обработано: {result.rows_processed}\n"
        f"Изменено: {result.rows_updated}\n"
        f"Применено: {'да' if result.applied else 'нет'}\n"
        f"Ошибок: {len(result.errors)}\n"
        f"Итог: {result.message}"
    )