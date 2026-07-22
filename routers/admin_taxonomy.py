"""Taxonomy & Data Quality Automation Center API."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_taxonomy import (BulkApply, BulkRequest, CategoryPatch, CategoryWrite, ClassifyApply,
    ClassifyPreview, ConflictResolve, MappingPatch, MappingWrite, QualityRulePatch, TreeWrite, WorkflowRun)
from services.admin_taxonomy_service import admin_category_taxonomy
from services.admin_taxonomy_application.classification import apply_classification, preview_classification
from services.admin_taxonomy_application.conflicts import list_conflicts, resolve_conflict
from services.admin_taxonomy_application.mappings import create_mapping, list_mappings, update_mapping
from services.admin_taxonomy_application.operations import (apply_batch, list_quality_rules,
    read_workflow, retry_workflow_by_id, rollback_batch, update_category_by_id, update_quality_rule)
from services.admin_taxonomy_application.serializers import batch_dict, operation_dict
from services.taxonomy_admin_service import (build_tree, category_dict, create_category, list_categories,
    preview_bulk, update_tree)
from services.taxonomy_workflow_service import run_workflow

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
    try: return update_category_by_id(db, category_id, body.model_dump(exclude_unset=True), actor=auth.actor_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
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
    return list_mappings(db, source=source, active=active, category_id=category_id, offset=offset, limit=limit)


@router.post("/taxonomy/mappings", status_code=201)
def mapping_create(body: MappingWrite, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return create_mapping(db, body.model_dump(), actor=auth.actor_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.patch("/taxonomy/mappings/{mapping_id}")
def mapping_update(mapping_id: int, body: MappingPatch, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return update_mapping(db, mapping_id, body.model_dump(exclude_unset=True))
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/taxonomy/classify/preview")
def classify_preview(body: ClassifyPreview, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    return preview_classification(db, body.model_dump())


@router.post("/taxonomy/classify/apply")
def classify_apply(body: ClassifyApply, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return apply_classification(db, body.model_dump(), actor=auth.actor_id)
    except TypeError as exc: raise HTTPException(422, str(exc)) from exc
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/taxonomy/conflicts")
def conflicts(city_slug: str | None = None, category_id: int | None = None, source: str | None = None,
    conflict_type: str | None = None, confidence_max: float | None = None, severity: str | None = None,
    route_eligible: bool | None = None, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    filters = locals().copy()
    return list_conflicts(db, filters, offset=offset, limit=limit)


@router.post("/taxonomy/conflicts/{conflict_id}/resolve")
def conflict_resolve(conflict_id: int, body: ConflictResolve, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return resolve_conflict(db, conflict_id, body.model_dump(), actor=auth.actor_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except TypeError as exc: raise HTTPException(422, str(exc)) from exc


@router.post("/taxonomy/bulk/preview")
def bulk_preview(body: BulkRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    batch = preview_bulk(db, **body.model_dump(), actor=auth.actor_id); return batch_dict(batch)


@router.post("/taxonomy/bulk/apply")
def bulk_apply(body: BulkApply, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return apply_batch(db, body.batch_id, actor=auth.actor_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.post("/taxonomy/bulk/{batch_id}/rollback")
def bulk_rollback(batch_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return rollback_batch(db, batch_id, actor=auth.actor_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc


@router.get("/quality/rules")
def quality_rules(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return list_quality_rules(db)


@router.patch("/quality/rules/{rule_id}")
def quality_rule_update(rule_id: int, body: QualityRulePatch, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return update_quality_rule(db, rule_id, body.model_dump(exclude_unset=True))
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/workflows/{workflow}/run")
def workflow_run(workflow: str, body: WorkflowRun, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return operation_dict(run_workflow(db, workflow=workflow, actor=auth.actor_id, **body.model_dump()))
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc


@router.get("/workflows/operations/{operation_id}")
def workflow_read(operation_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return read_workflow(db, operation_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc


@router.post("/workflows/operations/{operation_id}/retry")
def workflow_retry(operation_id: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try: return retry_workflow_by_id(db, operation_id)
    except LookupError as exc: raise HTTPException(404, str(exc)) from exc
