"""Транзакционная логика Taxonomy Manager."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.place import Place
from models.taxonomy import QualityRule, TaxonomyBulkBatch, TaxonomyConflict, TaxonomyDecision, TaxonomyMapping
from services.admin_audit_service import write_admin_audit_log
from services.route_policy_service import evaluate_category_policy
from services.taxonomy_rule_engine import ClassificationResult, classify_place, persist_decision


def category_dict(row: Category) -> dict[str, object]:
    return {"id": row.id, "code": row.code, "name": row.name, "display_name": row.display_name, "description": row.description,
        "parent_id": row.parent_id, "icon": row.icon, "color_token": row.color_token, "sort_order": row.sort_order,
        "is_active": row.is_active, "is_catalog_visible": row.is_catalog_visible, "is_searchable": row.is_searchable,
        "is_route_eligible": row.is_route_eligible, "default_visit_duration_minutes": row.default_visit_duration_minutes,
        "indoor_default": row.indoor_default, "outdoor_default": row.outdoor_default, "user_name": row.user_name,
        "admin_name": row.admin_name, "route_policy": row.route_policy, "route_contexts": row.route_contexts or [],
        "places_count": len(row.places), "archived_at": row.archived_at.isoformat() if row.archived_at else None}


def list_categories(db: Session, *, search: str | None, active: bool | None, parent_id: int | None, route_policy: str | None, offset: int, limit: int) -> dict[str, object]:
    query = db.query(Category)
    if search: query = query.filter(or_(Category.name.ilike(f"%{search}%"), Category.code.ilike(f"%{search}%"), Category.user_name.ilike(f"%{search}%")))
    if active is not None: query = query.filter(Category.is_active == active)
    if parent_id is not None: query = query.filter(Category.parent_id == parent_id)
    if route_policy: query = query.filter(Category.route_policy == route_policy)
    total = query.count()
    rows = query.order_by(Category.sort_order, Category.name).offset(offset).limit(limit).all()
    return {"items": [category_dict(row) for row in rows], "total": total, "offset": offset, "limit": limit}


def create_category(db: Session, *, data: dict[str, object], actor: str) -> Category:
    if db.query(Category).filter(Category.code == data["code"]).first(): raise ValueError("Код категории уже используется")
    _validate_parent(db, None, data.get("parent_id"))
    row = Category(**data)
    db.add(row); db.flush()
    write_admin_audit_log(db, actor=actor, action="taxonomy.category.created", entity_type="category", entity_id=row.id, new_value=category_dict(row))
    db.commit(); db.refresh(row); return row


def update_category(db: Session, *, row: Category, data: dict[str, object], actor: str) -> Category:
    old = category_dict(row)
    _validate_parent(db, row.id, data.get("parent_id"))
    for key, value in data.items(): setattr(row, key, value)
    if data.get("is_active") is False: row.archived_at = datetime.utcnow()
    if data.get("is_active") is True: row.archived_at = None
    write_admin_audit_log(db, actor=actor, action="taxonomy.category.updated", entity_type="category", entity_id=row.id, old_value=old, new_value=category_dict(row))
    db.commit(); db.refresh(row); return row


def update_tree(db: Session, *, nodes: list[dict[str, object]], actor: str) -> list[dict[str, object]]:
    rows = {row.id: row for row in db.query(Category).all()}
    for node in nodes:
        if int(node["id"]) not in rows: raise ValueError("Категория дерева не найдена")
        _validate_parent_map(rows, int(node["id"]), node.get("parent_id"), nodes)
    for node in nodes:
        row = rows[int(node["id"])]; row.parent_id = node.get("parent_id"); row.sort_order = int(node.get("sort_order", 0)); db.add(row)
    write_admin_audit_log(db, actor=actor, action="taxonomy.tree.updated", entity_type="taxonomy_tree", new_value={"nodes": nodes})
    db.commit(); return build_tree(db)


def build_tree(db: Session) -> list[dict[str, object]]:
    rows = db.query(Category).order_by(Category.sort_order, Category.name).all(); children: dict[int | None, list[Category]] = {}
    for row in rows: children.setdefault(row.parent_id, []).append(row)
    def node(row: Category, crumbs: list[str]) -> dict[str, object]:
        names = crumbs + [row.display_name]
        return {**category_dict(row), "breadcrumb": " / ".join(names), "children": [node(child, names) for child in children.get(row.id, [])]}
    return [node(row, []) for row in children.get(None, [])]


def mapping_hash(conditions: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(conditions, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:32]


def preview_bulk(db: Session, *, filters: dict[str, object], target_category_id: int | None, use_rule_engine: bool, update_route_eligibility: bool, idempotency_key: str, limit: int, actor: str) -> TaxonomyBulkBatch:
    existing = db.query(TaxonomyBulkBatch).filter(TaxonomyBulkBatch.idempotency_key == idempotency_key).first()
    if existing: return existing
    query = _filtered_places(db, filters); places = query.order_by(Place.id).limit(limit).all(); changes = []
    for place in places:
        category_id = target_category_id
        confidence = 1.0
        if use_rule_engine:
            result = classify_place(db, source=place.source, source_tags={}, title=place.title, description=place.short_description, current_category=place.category)
            category_id, confidence = result.category_id, result.confidence
        if category_id is None or category_id == place.category_id: continue
        category = db.query(Category).filter(Category.id == category_id, Category.is_active.is_(True)).first()
        if category is None: continue
        route = evaluate_category_policy(category)
        changes.append({"place_id": place.id, "title": place.title, "old_category_id": place.category_id, "old_category": place.canonical_category or place.category,
            "new_category_id": category.id, "new_category": category.code, "confidence": confidence, "old_route_eligible": place.is_route_eligible,
            "new_route_eligible": route.allowed if update_route_eligibility else place.is_route_eligible, "updated_at": place.updated_at.isoformat()})
    preview = {"count": len(changes), "examples": changes[:25], "changes": changes, "route_conflicts": sum(1 for item in changes if item["old_route_eligible"] != item["new_route_eligible"])}
    batch = TaxonomyBulkBatch(id=uuid4().hex, idempotency_key=idempotency_key, actor=actor, filters={**filters, "target_category_id": target_category_id, "use_rule_engine": use_rule_engine, "update_route_eligibility": update_route_eligibility}, preview=preview)
    db.add(batch); db.commit(); db.refresh(batch); return batch


def apply_bulk(db: Session, *, batch: TaxonomyBulkBatch, actor: str) -> TaxonomyBulkBatch:
    if batch.status == "applied": return batch
    if batch.status != "preview": raise ValueError("Пакет нельзя применить")
    changed = 0
    for item in batch.preview.get("changes", []):
        place = db.query(Place).filter(Place.id == item["place_id"]).first()
        if place is None or place.updated_at.isoformat() != item["updated_at"]: continue
        category = db.query(Category).filter(Category.id == item["new_category_id"], Category.is_active.is_(True)).first()
        if category is None: continue
        place.category_id = category.id; place.category = category.code; place.canonical_category = category.code
        if batch.filters.get("update_route_eligibility"): place.is_route_eligible = bool(item["new_route_eligible"])
        persist_decision(db, place_id=place.id, result=ClassificationResult(category.id, category.code, float(item["confidence"]), None, "Массовая переклассификация.", "bulk"), actor=actor, old_category_id=item["old_category_id"], batch_id=batch.id)
        db.add(place); changed += 1
    batch.status = "applied"; batch.applied_at = datetime.utcnow(); batch.result = {"changed": changed, "skipped": batch.preview["count"] - changed}
    write_admin_audit_log(db, actor=actor, action="taxonomy.bulk.applied", entity_type="taxonomy_batch", entity_id=batch.id, new_value=batch.result)
    db.commit(); return batch


def rollback_bulk(db: Session, *, batch: TaxonomyBulkBatch, actor: str) -> TaxonomyBulkBatch:
    if batch.status == "rolled_back": return batch
    if batch.status != "applied": raise ValueError("Откат доступен только применённому пакету")
    restored = 0
    for item in batch.preview.get("changes", []):
        place = db.query(Place).filter(Place.id == item["place_id"], Place.category_id == item["new_category_id"]).first()
        if place is None: continue
        place.category_id = item["old_category_id"]; place.category = item["old_category"]; place.canonical_category = item["old_category"]
        place.is_route_eligible = bool(item["old_route_eligible"]); db.add(place); restored += 1
    batch.status = "rolled_back"; batch.rolled_back_at = datetime.utcnow(); batch.rollback_result = {"restored": restored}
    write_admin_audit_log(db, actor=actor, action="taxonomy.bulk.rolled_back", entity_type="taxonomy_batch", entity_id=batch.id, new_value=batch.rollback_result)
    db.commit(); return batch


def _filtered_places(db: Session, filters: dict[str, object]):
    query = db.query(Place)
    if filters.get("city_slug"): query = query.join(City).filter(City.slug == filters["city_slug"])
    if filters.get("category_id") is not None: query = query.filter(Place.category_id == filters["category_id"])
    if filters.get("legacy_category"): query = query.filter(Place.category == filters["legacy_category"])
    if filters.get("source"): query = query.filter(Place.source == filters["source"])
    if filters.get("route_eligible") is not None: query = query.filter(Place.is_route_eligible == filters["route_eligible"])
    return query


def _validate_parent(db: Session, category_id: int | None, parent_id: object) -> None:
    if parent_id is None: return
    parent = db.query(Category).filter(Category.id == int(parent_id)).first()
    if parent is None: raise ValueError("Родительская категория не найдена")
    cursor = parent
    while cursor:
        if cursor.id == category_id: raise ValueError("Иерархия категорий содержит цикл")
        cursor = cursor.parent


def _validate_parent_map(rows: dict[int, Category], category_id: int, parent_id: object, nodes: list[dict[str, object]]) -> None:
    proposed = {int(node["id"]): node.get("parent_id") for node in nodes}; seen = {category_id}; cursor = parent_id
    while cursor is not None:
        cursor = int(cursor)
        if cursor in seen: raise ValueError("Иерархия категорий содержит цикл")
        if cursor not in rows: raise ValueError("Родительская категория не найдена")
        seen.add(cursor); cursor = proposed.get(cursor, rows[cursor].parent_id)
