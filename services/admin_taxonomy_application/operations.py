from __future__ import annotations

from sqlalchemy.orm import Session

from models.category import Category
from models.taxonomy import QualityRule, TaxonomyBulkBatch, WorkflowOperation
from services.admin_taxonomy_application.serializers import batch_dict, operation_dict, quality_rule_dict
from services.taxonomy_admin_service import apply_bulk, category_dict, rollback_bulk, update_category
from services.taxonomy_workflow_service import retry_workflow


def update_category_by_id(db: Session, category_id: int, data: dict[str, object], *, actor: str) -> dict[str, object]:
    row = db.query(Category).filter(Category.id == category_id).first()
    if row is None:
        raise LookupError("Категория не найдена")
    return category_dict(update_category(db, row=row, data=data, actor=actor))


def apply_batch(db: Session, batch_id: str, *, actor: str) -> dict[str, object]:
    batch = _batch(db, batch_id)
    return batch_dict(apply_bulk(db, batch=batch, actor=actor))


def rollback_batch(db: Session, batch_id: str, *, actor: str) -> dict[str, object]:
    batch = _batch(db, batch_id)
    return batch_dict(rollback_bulk(db, batch=batch, actor=actor))


def list_quality_rules(db: Session) -> list[dict[str, object]]:
    return [quality_rule_dict(row) for row in db.query(QualityRule).order_by(QualityRule.code).all()]


def update_quality_rule(db: Session, rule_id: int, data: dict[str, object]) -> dict[str, object]:
    row = db.query(QualityRule).filter(QualityRule.id == rule_id).first()
    if row is None:
        raise LookupError("Правило качества не найдено")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    return quality_rule_dict(row)


def read_workflow(db: Session, operation_id: str) -> dict[str, object]:
    return operation_dict(_workflow(db, operation_id))


def retry_workflow_by_id(db: Session, operation_id: str) -> dict[str, object]:
    return operation_dict(retry_workflow(db, _workflow(db, operation_id)))


def _batch(db: Session, batch_id: str) -> TaxonomyBulkBatch:
    row = db.query(TaxonomyBulkBatch).filter(TaxonomyBulkBatch.id == batch_id).first()
    if row is None:
        raise LookupError("Пакет не найден")
    return row


def _workflow(db: Session, operation_id: str) -> WorkflowOperation:
    row = db.query(WorkflowOperation).filter(WorkflowOperation.id == operation_id).first()
    if row is None:
        raise LookupError("Операция не найдена")
    return row
