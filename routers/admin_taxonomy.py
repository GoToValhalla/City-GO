"""Taxonomy & Data Quality Automation Center API."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.category import Category
from models.place import Place
from models.taxonomy import QualityRule, TaxonomyBulkBatch, TaxonomyConflict, TaxonomyMapping, WorkflowOperation
from schemas.admin_taxonomy import (BulkApply, BulkRequest, CategoryPatch, CategoryWrite, ClassifyApply,
    ClassifyPreview, ConflictResolve, MappingPatch, MappingWrite, QualityRulePatch, TreeWrite, WorkflowRun)
from services.admin_audit_service import write_admin_audit_log
from services.admin_taxonomy_service import admin_category_taxonomy
from services.taxonomy_admin_service import (apply_bulk, build_tree, category_dict, create_category, list_categories,
    mapping_hash, preview_bulk, rollback_bulk, update_category, update_tree)
from services.taxonomy_rule_engine import classify_place, persist_decision
from services.taxonomy_workflow_service import retry_workflow, run_workflow

router = APIRouter(prefix="/admin", tags=["admin-taxonomy"])

_CATEGORY_CONTROL_QUERY_PARAMS = {"city_slug"}


@router.get("/taxonomy/categories")
def categories(request: Request, search: str | None = None, active: bool | None = None, parent_id: int | None = None,
    route_policy: str | None = None, city_slug: str | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if set(request.query_params.keys()).issubset(_CATEGORY_CONTROL_QUERY_PARAMS):
        return {"categories": admin_category_taxonomy(db, city_slug=city_slug)}
    return list_categories(db, search=search, active=active, parent_id=parent_id, route_policy=route_policy, offset=offset, limit=limit)


@router.post("/taxonomy/categories", status_code=201)
def category_create(body: CategoryWrite, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return category_dict(create_category(db, data=body.model_dump(), actor=auth.actor_id))
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.patch("/taxonomy/categories/{category_id}")
def category_update(category_id: int, body: CategoryPatch, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(Category).filter(Category.id == category_id).first()
    if row is None: raise HTTPException(404, "Категория не найдена")
    try: return category_dict(update_category(db, row=row, data=body.model_dump(exclude_unset=True), actor=auth.actor_id))
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/taxonomy/tree")
def taxonomy_tree(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return build_tree(db)


@router.put("/taxonomy/tree")
def taxonomy_tree_update(body: TreeWrite, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    try: return update_tree(db, nodes=[node.model_dump() for node in body.nodes], actor=auth.actor_id)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/taxonomy/mappings")
def mappings(source: str | None = None, active: bool | None = None, category_id: int | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=300), auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db)) -> dict[str, object]:
    query = db.query(TaxonomyMapping)
    if source: query = query.filter(TaxonomyMapping.source == source)
    if active is not None: query = query.filter(TaxonomyMapping.active == active)
    if category_id: query = query.filter(TaxonomyMapping.target_category_id == category_id)
    total = query.count(); rows = query.order_by(TaxonomyMapping.priority.desc(), TaxonomyMapping.id).offset(offset).limit(limit).all()
    return {"items": [_mapping_dict(row) for row in rows], "total": total}


@router.post("/taxonomy/mappings", status_code=201)
def mapping_create(body: MappingWrite, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if not db.query(Category).filter(Category.id == body.target_category_id).first(): raise HTTPException(404, "Категория не найдена")
    row = TaxonomyMapping(**body.model_dump(), conditions_hash=mapping_hash(body.conditions), created_by=auth.actor_id)
    db.add(row)
    try: db.commit()
    except Exception as exc: db.rollback(); raise HTTPException(409, "Такое правило уже существует") from exc
    db.refresh(row); return _mapping_dict(row)


@router.patch("/taxonomy/mappings/{mapping_id}")
def mapping_update(mapping_id: int, body: MappingPatch, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(TaxonomyMapping).filter(TaxonomyMapping.id == mapping_id).first()
    if row is None: raise HTTPException(404, "Правило не найдено")
    for key, value in body.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    if body.conditions is not None: row.conditions_hash = mapping_hash(body.conditions)
    db.commit(); db.refresh(row); return _mapping_dict(row)


@router.post("/taxonomy/classify/preview")
def classify_preview(body: ClassifyPreview, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    data = body.model_dump(); data.pop("place_id", None)
    result = classify_place(db, **data)
    return result.to_dict()


@router.post("/taxonomy/classify/apply")
def classify_apply(body: ClassifyApply, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if body.place_id is None: raise HTTPException(422, "Для применения требуется place_id")
    place = db.query(Place).filter(Place.id == body.place_id).first()
    if place is None: raise HTTPException(404, "Место не найдено")
    data = body.model_dump(exclude={"place_id", "expected_category_id"})
    result = classify_place(db, **data)
    if result.decision not in {"auto_apply", "manual"}: raise HTTPException(409, "Низкоуверенную классификацию нельзя применить без ручного выбора")
    if body.expected_category_id is not None and place.category_id != body.expected_category_id: raise HTTPException(409, "Категория места изменилась после preview")
    category = db.query(Category).filter(Category.id == result.category_id, Category.is_active.is_(True)).first()
    if category is None: raise HTTPException(409, "Рекомендованная категория недоступна")
    old = place.category_id; place.category_id = category.id; place.category = category.code; place.canonical_category = category.code
    persist_decision(db, place_id=place.id, result=result, actor=auth.actor_id, old_category_id=old)
    write_admin_audit_log(db, actor=auth.actor_id, action="taxonomy.classification.applied", entity_type="place", entity_id=place.id,
        old_value={"category_id": old}, new_value={"category_id": category.id, "explanation": result.explanation})
    db.commit(); return {**result.to_dict(), "applied": True}


@router.get("/taxonomy/conflicts")
def conflicts(city_slug: str | None = None, category_id: int | None = None, source: str | None = None,
    conflict_type: str | None = None, confidence_max: float | None = None, severity: str | None = None,
    route_eligible: bool | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    query = db.query(TaxonomyConflict).join(Place)
    if city_slug: query = query.join(Place.city).filter_by(slug=city_slug)
    if category_id: query = query.filter(TaxonomyConflict.current_category_id == category_id)
    if source: query = query.filter(TaxonomyConflict.source == source)
    if conflict_type: query = query.filter(TaxonomyConflict.conflict_type == conflict_type)
    if confidence_max is not None: query = query.filter(TaxonomyConflict.confidence <= confidence_max)
    if severity: query = query.filter(TaxonomyConflict.severity == severity)
    if route_eligible is not None: query = query.filter(Place.is_route_eligible == route_eligible)
    query = query.filter(TaxonomyConflict.status == "open"); total = query.count()
    rows = query.order_by(TaxonomyConflict.created_at, TaxonomyConflict.id).offset(offset).limit(limit).all()
    return {"items": [_conflict_dict(row) for row in rows], "total": total}


@router.post("/taxonomy/conflicts/{conflict_id}/resolve")
def conflict_resolve(conflict_id: int, body: ConflictResolve, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    conflict = db.query(TaxonomyConflict).filter(TaxonomyConflict.id == conflict_id, TaxonomyConflict.status == "open").first()
    if conflict is None: raise HTTPException(404, "Активный конфликт не найден")
    place = db.query(Place).filter(Place.id == conflict.place_id).first()
    category_id = body.category_id or conflict.recommended_category_id
    if body.action in {"accept", "choose", "create_mapping", "apply_similar"}:
        category = db.query(Category).filter(Category.id == category_id, Category.is_active.is_(True)).first()
        if category is None: raise HTTPException(422, "Выберите активную категорию")
        old = place.category_id; place.category_id = category.id; place.category = category.code; place.canonical_category = category.code
        if body.create_mapping or body.action == "create_mapping":
            source_key = str(conflict.details.get("source_key") or "legacy_category"); source_value = str(conflict.details.get("source_value") or place.category)
            db.add(TaxonomyMapping(source=conflict.source or "legacy", source_key=source_key, source_value=source_value,
                target_category_id=category.id, priority=200, confidence=1, conditions={}, conditions_hash="-", created_by=auth.actor_id, comment=body.comment))
        persist_decision(db, place_id=place.id, result=classify_place(db, source=None, source_tags={}, title=place.title,
            description=place.short_description, current_category=place.category, manual_category_id=category.id), actor=auth.actor_id, old_category_id=old)
    elif body.action == "exclude": place.is_route_eligible = False
    conflict.status = "deferred" if body.action == "defer" else "resolved"; conflict.resolution = body.model_dump(); conflict.resolved_by = auth.actor_id; conflict.resolved_at = datetime.utcnow()
    write_admin_audit_log(db, actor=auth.actor_id, action="taxonomy.conflict.resolved", entity_type="taxonomy_conflict", entity_id=conflict.id, new_value=body.model_dump())
    db.commit(); return {"resolved": True, "next_available": db.query(TaxonomyConflict).filter(TaxonomyConflict.status == "open").count() > 0}


@router.post("/taxonomy/bulk/preview")
def bulk_preview(body: BulkRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    batch = preview_bulk(db, **body.model_dump(), actor=auth.actor_id); return _batch_dict(batch)


@router.post("/taxonomy/bulk/apply")
def bulk_apply(body: BulkApply, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    batch = db.query(TaxonomyBulkBatch).filter(TaxonomyBulkBatch.id == body.batch_id).first()
    if batch is None: raise HTTPException(404, "Пакет не найден")
    try: return _batch_dict(apply_bulk(db, batch=batch, actor=auth.actor_id))
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.post("/taxonomy/bulk/{batch_id}/rollback")
def bulk_rollback(batch_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    batch = db.query(TaxonomyBulkBatch).filter(TaxonomyBulkBatch.id == batch_id).first()
    if batch is None: raise HTTPException(404, "Пакет не найден")
    try: return _batch_dict(rollback_bulk(db, batch=batch, actor=auth.actor_id))
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/quality/rules")
def quality_rules(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [_quality_rule_dict(row) for row in db.query(QualityRule).order_by(QualityRule.code).all()]


@router.patch("/quality/rules/{rule_id}")
def quality_rule_update(rule_id: int, body: QualityRulePatch, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(QualityRule).filter(QualityRule.id == rule_id).first()
    if row is None: raise HTTPException(404, "Правило качества не найдено")
    for key, value in body.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    db.commit(); return _quality_rule_dict(row)


@router.post("/workflows/{workflow}/run")
def workflow_run(workflow: str, body: WorkflowRun, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return _operation_dict(run_workflow(db, workflow=workflow, actor=auth.actor_id, **body.model_dump()))
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc


@router.get("/workflows/operations/{operation_id}")
def workflow_read(operation_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(WorkflowOperation).filter(WorkflowOperation.id == operation_id).first()
    if row is None: raise HTTPException(404, "Операция не найдена")
    return _operation_dict(row)


@router.post("/workflows/operations/{operation_id}/retry")
def workflow_retry(operation_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(WorkflowOperation).filter(WorkflowOperation.id == operation_id).first()
    if row is None: raise HTTPException(404, "Операция не найдена")
    return _operation_dict(retry_workflow(db, row))


def _mapping_dict(row: TaxonomyMapping) -> dict[str, object]: return {key: getattr(row, key) for key in ("id", "source", "source_key", "source_value", "target_category_id", "priority", "confidence", "active", "conditions", "fallback", "comment", "created_by")}
def _conflict_dict(row: TaxonomyConflict) -> dict[str, object]: return {"id": row.id, "place_id": row.place_id, "place_title": row.place.title if hasattr(row, "place") else None, "conflict_type": row.conflict_type, "severity": row.severity, "source": row.source, "confidence": row.confidence, "current_category_id": row.current_category_id, "recommended_category_id": row.recommended_category_id, "details": row.details, "status": row.status}
def _batch_dict(row: TaxonomyBulkBatch) -> dict[str, object]: return {"id": row.id, "status": row.status, "filters": row.filters, "preview": row.preview, "result": row.result, "rollback_result": row.rollback_result}
def _quality_rule_dict(row: QualityRule) -> dict[str, object]: return {key: getattr(row, key) for key in ("id", "code", "name_ru", "severity", "entity_type", "active", "parameters", "auto_fix_available", "blocking_publication", "blocking_route_eligibility")}
def _operation_dict(row: WorkflowOperation) -> dict[str, object]: return {"id": row.id, "workflow": row.workflow, "request_id": row.request_id, "entity_type": row.entity_type, "entity_id": row.entity_id, "status": row.status, "current_step": row.current_step, "steps": row.steps, "retry_count": row.retry_count, "max_retries": row.max_retries, "error_message": row.error_message}
