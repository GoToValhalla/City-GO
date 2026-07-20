"""Safe admin backlog reduction workflow: plan, dry-run, apply, result."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.admin_operation import AdminOperation
from models.data_foundation import CityEnrichmentRun, EnrichmentTask
from models.place import Place
from schemas.admin_backlog_reduction import BacklogReductionApplyRequest, BacklogReductionDryRunRequest, BacklogReductionResult
from services.admin_audit_service import write_admin_audit_log
from services.admin_backlog_breakdown_service import build_admin_backlog_breakdown
from services.admin_backlog_clauses import content_gap_clause, queue_clause, reason_clause, service_category_clause
from services.publication_state_writer import (
    InvalidPublicationTransition,
    REASON_ENRICHMENT_BACKLOG,
    reconcile_published_place_state,
    transition_place_publication,
)
from services.route_eligibility_policy import evaluate_place_route_eligibility

CONFIRMATION_TEXT = "APPLY"
OPERATION_TYPE = "backlog_reduction"
ACTIVE_TASK_STATUSES = ("queued", "running", "processing", "locked")
QUEUE_TASK_TYPES = {
    "enqueue_description_enrichment": "description_enrichment",
    "enqueue_photo_discovery": "photo_discovery",
    "enqueue_address_recovery": "address_recovery",
    "auto_recheck_verification_backlog": "verification_recheck",
}


@dataclass(frozen=True)
class ActionSpec:
    code: str
    title: str
    description: str
    queue_code: str
    reason_codes: tuple[str, ...]
    risk_level: str
    enabled: bool
    disabled_reason: str | None
    owner: str
    expected_effect: str
    max_batch_size: int = 500


ACTION_SPECS: tuple[ActionSpec, ...] = (
    ActionSpec("recompute_route_eligibility", "Пересчитать готовность к маршрутам", "Сверяет места с текущими правилами маршрутов.", "route_blockers", ("manual_disabled", "service_category", "unknown_category"), "safe", True, None, "data", "Убирает расхождение между флагом маршрута и правилами."),
    ActionSpec("exclude_service_places_from_routes", "Убрать сервисные точки из маршрутов", "Оставляет места опубликованными, но выключает их из маршрутов.", "route_excluded", ("pharmacy_medical", "bank_atm", "transport_bus_stop", "parking_fuel", "other_service"), "safe", True, None, "data", "Сервисные места перестают попадать в прогулочные маршруты."),
    ActionSpec("classify_unknown_categories_deterministic", "Разобрать очевидные категории", "Назначает категорию только при уверенном совпадении по названию.", "route_unknown", ("unknown_category", "empty_category", "unmapped_category"), "safe", True, None, "taxonomy", "Очевидно распознанные места переходят в понятные категории."),
    ActionSpec("normalize_manual_review_backlog", "Разложить очередь разбора", "Переносит очевидные автоматические элементы в автоочередь.", "manual_review", ("legacy_needs_review", "overlaps_with_verification", "overlaps_with_content_gaps", "overlaps_with_low_confidence"), "safe", True, None, "content", "Снижает видимую ручную очередь без публикации мест."),
    ActionSpec("enqueue_description_enrichment", "Поставить описания в очередь", "Создаёт задачу на обогащение, не пишет выдуманный текст.", "no_description", ("description_null", "description_empty", "description_equals_title", "description_too_short", "placeholder_description"), "safe", True, None, "automation", "Очередь описаний становится обрабатываемой."),
    ActionSpec("enqueue_photo_discovery", "Поставить фото в очередь", "Создаёт задачу на поиск фото, не подставляет фейковые изображения.", "no_photo", ("published_without_any_photo", "route_ready_without_photo"), "safe", True, None, "automation", "Фото уходят в обработку."),
    ActionSpec("enqueue_address_recovery", "Поставить адреса в очередь", "Создаёт задачу на восстановление адресов, не выдумывает адрес.", "no_address", ("address_null", "address_empty", "coordinates_without_address"), "safe", True, None, "automation", "Адреса уходят в обработку."),
    ActionSpec("auto_recheck_verification_backlog", "Поставить проверку данных в очередь", "Создаёт задачу перепроверки, не подтверждает место без фактов.", "needs_verification", ("needs_recheck", "unverified", "route_relevant_verification"), "safe", True, None, "automation", "Проверка становится планируемой работой."),
    ActionSpec("recompute_low_confidence", "Пересчитать низкую уверенность", "Нет безопасного правила пересчёта для всех источников.", "low_confidence", ("data_confidence_low", "confidence_unknown"), "safe", False, "Нет безопасного локального правила пересчёта без источников.", "automation", "Будет включено после появления правил пересчёта."),
)


def build_reduction_plan(db: Session) -> dict[str, object]:
    breakdown = build_admin_backlog_breakdown(db)
    queues = list(breakdown["queues"])
    actions = [_action_payload(db, spec) for spec in ACTION_SPECS]
    summary = {
        "total_auto_fixable": int(breakdown["summary"]["auto_fixable_places"]),
        "total_manual_after_classification": _manual_after_classification(db),
        "route_blockers_reducible": _candidate_count(db, ACTION_SPECS[0]),
        "unknown_categories_auto_classifiable": len(_classifiable_unknowns(db, 10000)),
        "manual_review_reclassifiable": _manual_reclassifiable_count(db),
        "verification_auto_recheckable": _candidate_count(db, _spec("auto_recheck_verification_backlog")),
        "content_enrichment_queueable": _count(db, content_gap_clause()),
    }
    return {"generated_at": datetime.utcnow(), "summary": summary, "actions": actions, "queues": queues}


def dry_run(db: Session, request: BacklogReductionDryRunRequest) -> BacklogReductionResult:
    spec = _spec(request.action_code)
    before = _summary(db)
    if not spec.enabled:
        return _result(spec, True, 0, 0, 0, 0, 0, request.limit, before, before, message=spec.disabled_reason or "Действие пока недоступно.", status="unsupported")
    places = _candidates(db, spec, request)
    outcome = _simulate(spec, places)
    estimated = _estimated_counts(before, outcome["would_change_count"] + outcome["queued_count"])
    return _result(spec, True, len(places), outcome["would_change_count"], outcome["skipped_count"], 0, outcome["queued_count"], request.limit, before, estimated, samples=_samples(places, request.include_samples), skipped_reasons=outcome["skipped_reasons"], message=_message(spec, True, outcome))


def apply(db: Session, request: BacklogReductionApplyRequest, *, actor: str) -> BacklogReductionResult:
    if request.confirmation_text != CONFIRMATION_TEXT:
        raise HTTPException(status_code=409, detail="Для применения введите APPLY.")
    spec = _spec(request.action_code)
    if not spec.enabled or spec.risk_level != "safe":
        raise HTTPException(status_code=409, detail=spec.disabled_reason or "Для этого действия нет безопасного применения.")
    before = _summary(db)
    places = _candidates(db, spec, request)
    outcome = _apply_action(db, spec, places, actor=actor or "admin")
    after = _summary(db)
    result = _result(spec, False, len(places), outcome["changed_count"], outcome["skipped_count"], outcome["failed_count"], outcome["queued_count"], request.limit, before, after, samples=_samples(places, request.include_samples), skipped_reasons=outcome["skipped_reasons"], errors=outcome["errors"], message=_message(spec, False, outcome), status="partial" if outcome["failed_count"] else "applied")
    op = _record_operation(db, spec, actor, request, result)
    audit = write_admin_audit_log(db, actor=actor, action="backlog_reduction_apply", entity_type="admin_operation", entity_id=op.id, old_value=before, new_value=result.model_dump(mode="json"), reason=spec.title)
    db.commit()
    result.job_id = op.id
    result.audit_id = audit.id
    return result


def get_job_result(db: Session, job_id: int) -> dict[str, object] | None:
    op = db.query(AdminOperation).filter(AdminOperation.id == job_id, AdminOperation.operation_type == OPERATION_TYPE).first()
    if op is None:
        return None
    return {
        "id": op.id,
        "action_code": str((op.result or {}).get("action_code") or ""),
        "status": op.status,
        "started_at": op.created_at,
        "finished_at": op.updated_at,
        "requested_by": op.actor,
        "dry_run": bool((op.result or {}).get("dry_run")),
        "limit": int((op.result or {}).get("limit") or 0),
        "changed_count": int((op.result or {}).get("changed_count") or 0),
        "skipped_count": int((op.result or {}).get("skipped_count") or 0),
        "failed_count": int((op.result or {}).get("failed_count") or 0),
        "queued_count": int((op.result or {}).get("queued_count") or 0),
        "result_json": op.result or {},
    }


def _action_payload(db: Session, spec: ActionSpec) -> dict[str, object]:
    affected = _candidate_count(db, spec) if spec.enabled else 0
    return {
        "code": spec.code,
        "title": spec.title,
        "description": spec.description,
        "queue_code": spec.queue_code,
        "reason_codes": list(spec.reason_codes),
        "risk_level": spec.risk_level,
        "enabled": spec.enabled,
        "disabled_reason": spec.disabled_reason,
        "dry_run_endpoint": "/admin/overview/backlog-reduction/dry-run",
        "apply_endpoint": "/admin/overview/backlog-reduction/apply",
        "requires_confirmation": True,
        "max_batch_size": spec.max_batch_size,
        "owner": spec.owner,
        "expected_effect": spec.expected_effect,
        "visible": True,
        "affected_count": affected,
    }


def _candidates(db: Session, spec: ActionSpec, request: BacklogReductionDryRunRequest) -> list[Place]:
    query = db.query(Place)
    if request.city_id is not None:
        query = query.filter(Place.city_id == request.city_id)
    if spec.code == "recompute_route_eligibility":
        return _stale_route_places(query.order_by(Place.id).limit(spec.max_batch_size).all(), request.limit)
    if spec.code == "classify_unknown_categories_deterministic":
        return _classifiable_unknowns(db, request.limit, city_id=request.city_id)
    clause = reason_clause(request.reason_code) if request.reason_code else queue_clause(request.queue_code or spec.queue_code)
    if spec.code == "exclude_service_places_from_routes":
        clause = service_category_clause() & Place.is_route_eligible.is_(True)
    if spec.code == "normalize_manual_review_backlog":
        clause = queue_clause("manual_review")
    return query.filter(clause).order_by(Place.id).limit(min(request.limit, spec.max_batch_size)).all()


def _stale_route_places(places: list[Place], limit: int) -> list[Place]:
    stale = []
    for place in places:
        verdict = evaluate_place_route_eligibility(place)
        reason = None if verdict.eligible else ",".join(verdict.reasons)
        if place.is_route_eligible is not verdict.eligible or (not verdict.eligible and (place.route_exclusion_reason or "") != (reason or "")):
            stale.append(place)
        if len(stale) >= limit:
            break
    return stale


def _classifiable_unknowns(db: Session, limit: int, city_id: int | None = None) -> list[Place]:
    query = db.query(Place).filter(queue_clause("route_unknown")).order_by(Place.id)
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)
    return [place for place in query.limit(limit * 3).all() if _classify(place)[1] == "high"][:limit]


def _apply_action(db: Session, spec: ActionSpec, places: list[Place], *, actor: str) -> dict[str, object]:
    if _task_type(spec):
        return _queue_enrichment_tasks(db, spec, places, actor=actor)
    changed = skipped = 0
    skipped_reasons: dict[str, int] = {}
    for place in places:
        did_change, reason = _apply_place_change(db, spec, place, actor=actor)
        changed += int(did_change)
        if reason:
            skipped += 1
            skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
    db.flush()
    return {"changed_count": changed, "skipped_count": skipped, "failed_count": 0, "queued_count": 0, "skipped_reasons": skipped_reasons, "errors": []}


def _apply_place_change(db: Session, spec: ActionSpec, place: Place, *, actor: str) -> tuple[bool, str | None]:
    if spec.code == "recompute_route_eligibility":
        if not place.is_published:
            return False, "not_published"
        verdict = evaluate_place_route_eligibility(place)
        reason = None if verdict.eligible else ",".join(verdict.reasons)
        changed = reconcile_published_place_state(
            db, place, route_eligible=verdict.eligible, route_exclusion_reason=reason,
            actor=actor, source="admin_backlog_reduction",
        )
        return changed, None if changed else "already_current"
    if spec.code == "exclude_service_places_from_routes":
        if place.is_route_eligible is not True:
            return False, "already_excluded"
        if not place.is_published:
            return False, "not_published"
        changed = reconcile_published_place_state(
            db, place, route_eligible=False, route_exclusion_reason="service_category",
            actor=actor, source="admin_backlog_reduction",
        )
        return changed, None if changed else "already_current"
    if spec.code == "classify_unknown_categories_deterministic":
        category, confidence = _classify(place)
        if confidence != "high" or not category:
            return False, "ambiguous_category"
        place.canonical_category = category
        if place.is_published:
            db.flush()
            verdict = evaluate_place_route_eligibility(place)
            reason = None if verdict.eligible else ",".join(verdict.reasons)
            reconcile_published_place_state(
                db, place, route_eligible=verdict.eligible, route_exclusion_reason=reason,
                actor=actor, source="admin_backlog_reduction",
            )
        return True, None
    if spec.code == "normalize_manual_review_backlog":
        if place.publication_status != "needs_review":
            return False, "explicit_manual_required"
        if _manual_safe_to_auto(place):
            try:
                transition_place_publication(
                    db, place, to_status="auto_backlog", reason_code=REASON_ENRICHMENT_BACKLOG,
                    actor=actor, source="admin_backlog_reduction",
                )
            except InvalidPublicationTransition:
                pass
            return True, None
        return False, "unknown_manual_reason"
    return False, "unsupported"


def _queue_enrichment_tasks(db: Session, spec: ActionSpec, places: list[Place], *, actor: str) -> dict[str, object]:
    task_type = _task_type(spec)
    assert task_type is not None
    run = CityEnrichmentRun(
        run_type="backlog_reduction",
        status="queued",
        stage=spec.code,
        progress_total=0,
        progress_done=0,
        summary={"action_code": spec.code, "task_type": task_type, "requested_by": actor, "place_ids": [place.id for place in places]},
    )
    db.add(run)
    db.flush()
    queued = skipped = 0
    skipped_reasons: dict[str, int] = {}
    for place in places:
        created, reason = _enqueue_task(db, run, place, task_type, spec, actor)
        if created:
            queued += 1
        else:
            skipped += 1
            skipped_reasons[reason or "not_queued"] = skipped_reasons.get(reason or "not_queued", 0) + 1
    run.progress_total = queued
    run.status = "queued" if queued else "skipped"
    run.summary = {**(run.summary or {}), "queued_count": queued, "skipped_count": skipped, "skipped_reasons": skipped_reasons}
    db.flush()
    return {"changed_count": 0, "skipped_count": skipped, "failed_count": 0, "queued_count": queued, "skipped_reasons": skipped_reasons, "errors": []}


def _enqueue_task(db: Session, run: CityEnrichmentRun, place: Place, task_type: str, spec: ActionSpec, actor: str) -> tuple[bool, str | None]:
    existing = (
        db.query(EnrichmentTask.id)
        .filter(
            EnrichmentTask.place_id == place.id,
            EnrichmentTask.task_type == task_type,
            EnrichmentTask.status.in_(ACTIVE_TASK_STATUSES),
        )
        .first()
    )
    if existing is not None:
        return False, "already_queued"
    db.add(
        EnrichmentTask(
            run_id=run.id,
            city_id=place.city_id,
            place_id=place.id,
            task_type=task_type,
            status="queued",
            priority=_task_priority(spec),
            payload={
                "source": "backlog_reduction",
                "action_code": spec.code,
                "queue_code": spec.queue_code,
                "reason_codes": list(spec.reason_codes),
                "requested_by": actor,
            },
        )
    )
    return True, None


def _simulate(spec: ActionSpec, places: list[Place]) -> dict[str, object]:
    would_change = queued = skipped = 0
    skipped_reasons: dict[str, int] = {}
    for place in places:
        if _task_type(spec):
            queued += 1
        elif spec.code == "normalize_manual_review_backlog" and not _manual_safe_to_auto(place):
            skipped += 1
            skipped_reasons["unknown_manual_reason"] = skipped_reasons.get("unknown_manual_reason", 0) + 1
        else:
            would_change += 1
    return {"would_change_count": would_change, "queued_count": queued, "skipped_count": skipped, "skipped_reasons": skipped_reasons}


def _task_type(spec: ActionSpec) -> str | None:
    return QUEUE_TASK_TYPES.get(spec.code)


def _task_priority(spec: ActionSpec) -> int:
    if spec.code == "auto_recheck_verification_backlog":
        return 40
    if spec.code == "enqueue_address_recovery":
        return 50
    if spec.code == "enqueue_photo_discovery":
        return 70
    return 80


def _manual_safe_to_auto(place: Place) -> bool:
    return bool(place.verification_status in {"needs_recheck", "unverified"} or place.existence_confidence_level in {"low", "unknown"} or not place.image_url or not place.address or not place.short_description)


def _classify(place: Place) -> tuple[str | None, str]:
    text = f"{place.title or ''} {place.category or ''}".casefold()
    rules = (
        (("аптек", "pharmacy"), "pharmacy"), (("банк", "банкомат", "atm", "bank"), "bank"),
        (("останов", "bus stop", "transport stop"), "bus_stop"), (("музей", "museum"), "museum"),
        (("парк", "park"), "park"), (("памятник", "monument"), "monument"),
        (("театр", "theatre", "theater"), "theatre"), (("ресторан", "restaurant"), "restaurant"),
        (("кафе", "coffee", "cafe"), "cafe"),
    )
    match = next(((category, "high") for needles, category in rules if any(needle in text for needle in needles)), None)
    return match or (None, "low")


def _record_operation(db: Session, spec: ActionSpec, actor: str, request: BacklogReductionApplyRequest, result: BacklogReductionResult) -> AdminOperation:
    op = AdminOperation(operation_type=OPERATION_TYPE, status="completed", actor=actor or "admin", city_slug=None, place_ids=[int(sample["id"]) for sample in result.samples if "id" in sample], result={**result.model_dump(mode="json"), "limit": request.limit})
    db.add(op)
    db.flush()
    return op


def _result(spec: ActionSpec, dry: bool, affected: int, changed: int, skipped: int, failed: int, queued: int, limit: int, before: dict[str, int], after: dict[str, int], *, samples: list[dict[str, object]] | None = None, skipped_reasons: dict[str, int] | None = None, errors: list[str] | None = None, message: str, status: str = "planned") -> BacklogReductionResult:
    return BacklogReductionResult(action_code=spec.code, status=status, dry_run=dry, affected_count=affected, changed_count=changed, skipped_count=skipped, failed_count=failed, queued_count=queued, unsupported_count=0 if spec.enabled else affected, before_counts=before, after_counts={} if dry else after, estimated_after_counts=after if dry else {}, samples=samples or [], skipped_reasons=skipped_reasons or {}, errors=errors or [], limit=limit, message=message)


def _samples(places: list[Place], include: bool) -> list[dict[str, object]]:
    return [{"id": place.id, "title": place.title, "category": place.canonical_category or place.category, "publication_status": place.publication_status} for place in places[:10]] if include else []


def _summary(db: Session) -> dict[str, int]:
    return {key: int(value) for key, value in build_admin_backlog_breakdown(db)["summary"].items()}


def _estimated_counts(before: dict[str, int], delta: int) -> dict[str, int]:
    return {**before, "total_problem_signals": max(0, before.get("total_problem_signals", 0) - delta)}


def _candidate_count(db: Session, spec: ActionSpec) -> int:
    return len(_candidates(db, spec, BacklogReductionDryRunRequest(action_code=spec.code, limit=spec.max_batch_size)))


def _manual_reclassifiable_count(db: Session) -> int:
    return len([place for place in db.query(Place).filter(Place.publication_status == "needs_review").limit(10000).all() if _manual_safe_to_auto(place)])


def _manual_after_classification(db: Session) -> int:
    total = int(db.query(Place).filter(queue_clause("manual_review")).count() or 0)
    return max(0, total - _manual_reclassifiable_count(db))


def _count(db: Session, clause) -> int:
    if clause is None:
        return 0
    return int(db.query(Place.id).filter(clause).distinct().count() or 0)


def _spec(code: str) -> ActionSpec:
    found = next((spec for spec in ACTION_SPECS if spec.code == code), None)
    if found is None:
        raise HTTPException(status_code=404, detail="Действие не найдено.")
    return found


def _message(spec: ActionSpec, dry: bool, outcome: dict[str, object]) -> str:
    prefix = "Пробный запуск" if dry else "Применение завершено"
    return f"{prefix}: {spec.title}. Изменений: {outcome.get('would_change_count', outcome.get('changed_count', 0))}, поставлено в очередь: {outcome.get('queued_count', 0)}, пропущено: {outcome.get('skipped_count', 0)}."
