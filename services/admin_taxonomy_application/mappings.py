from __future__ import annotations

from sqlalchemy.orm import Session

from models.category import Category
from models.taxonomy import TaxonomyMapping
from services.admin_taxonomy_application.serializers import mapping_dict
from services.taxonomy_admin_service import mapping_hash


def list_mappings(db: Session, *, source: str | None, active: bool | None,
                  category_id: int | None, offset: int, limit: int) -> dict[str, object]:
    query = db.query(TaxonomyMapping)
    if source:
        query = query.filter(TaxonomyMapping.source == source)
    if active is not None:
        query = query.filter(TaxonomyMapping.active == active)
    if category_id:
        query = query.filter(TaxonomyMapping.target_category_id == category_id)
    total = query.count()
    rows = query.order_by(TaxonomyMapping.priority.desc(), TaxonomyMapping.id).offset(offset).limit(limit).all()
    return {"items": [mapping_dict(row) for row in rows], "total": total}


def create_mapping(db: Session, data: dict[str, object], *, actor: str) -> dict[str, object]:
    if not db.query(Category).filter(Category.id == data["target_category_id"]).first():
        raise LookupError("Категория не найдена")
    conditions = data.get("conditions") or {}
    row = TaxonomyMapping(**data, conditions_hash=mapping_hash(conditions), created_by=actor)
    db.add(row)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise ValueError("Такое правило уже существует") from exc
    db.refresh(row)
    return mapping_dict(row)


def update_mapping(db: Session, mapping_id: int, data: dict[str, object]) -> dict[str, object]:
    row = db.query(TaxonomyMapping).filter(TaxonomyMapping.id == mapping_id).first()
    if row is None:
        raise LookupError("Правило не найдено")
    for key, value in data.items():
        setattr(row, key, value)
    if "conditions" in data:
        row.conditions_hash = mapping_hash(data["conditions"] or {})
    db.commit()
    db.refresh(row)
    return mapping_dict(row)
