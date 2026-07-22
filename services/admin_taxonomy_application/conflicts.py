from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.category import Category
from models.place import Place
from models.taxonomy import TaxonomyConflict, TaxonomyMapping
from services.admin_audit_service import write_admin_audit_log
from services.admin_taxonomy_application.serializers import conflict_dict
from services.publication_state_writer import InvalidPublicationTransition, reconcile_published_place_state
from services.taxonomy_rule_engine import classify_place, persist_decision


def list_conflicts(db: Session, filters: dict[str, object], *, offset: int,
                   limit: int) -> dict[str, object]:
    query = db.query(TaxonomyConflict).join(Place)
    clauses = (("category_id", TaxonomyConflict.current_category_id), ("source", TaxonomyConflict.source),
               ("conflict_type", TaxonomyConflict.conflict_type), ("severity", TaxonomyConflict.severity),
               ("confidence_max", TaxonomyConflict.confidence), ("route_eligible", Place.is_route_eligible))
    if filters.get("city_slug"):
        query = query.join(Place.city).filter_by(slug=filters["city_slug"])
    for key, column in clauses:
        value = filters.get(key)
        if value is not None:
            query = query.filter(column <= value if key == "confidence_max" else column == value)
    query = query.filter(TaxonomyConflict.status == "open")
    total = query.count()
    rows = query.order_by(TaxonomyConflict.created_at, TaxonomyConflict.id).offset(offset).limit(limit).all()
    return {"items": [conflict_dict(row) for row in rows], "total": total}


def resolve_conflict(db: Session, conflict_id: int, data: dict[str, object], *, actor: str) -> dict[str, object]:
    conflict = db.query(TaxonomyConflict).filter(
        TaxonomyConflict.id == conflict_id, TaxonomyConflict.status == "open").first()
    if conflict is None:
        raise LookupError("Активный конфликт не найден")
    place = db.query(Place).filter(Place.id == conflict.place_id).first()
    category_id = data.get("category_id") or conflict.recommended_category_id
    if data["action"] in {"accept", "choose", "create_mapping", "apply_similar"}:
        _apply_category(db, conflict, place, category_id, data, actor)
    elif data["action"] == "exclude" and place.is_published:
        _exclude_route(db, place, actor)
    conflict.status = "deferred" if data["action"] == "defer" else "resolved"
    conflict.resolution, conflict.resolved_by, conflict.resolved_at = data, actor, datetime.utcnow()
    write_admin_audit_log(db, actor=actor, action="taxonomy.conflict.resolved",
                          entity_type="taxonomy_conflict", entity_id=conflict.id, new_value=data)
    db.commit()
    remaining = db.query(TaxonomyConflict).filter(TaxonomyConflict.status == "open").count()
    return {"resolved": True, "next_available": remaining > 0}


def _apply_category(db: Session, conflict: TaxonomyConflict, place: Place, category_id: object,
                    data: dict[str, object], actor: str) -> None:
    category = db.query(Category).filter(Category.id == category_id, Category.is_active.is_(True)).first()
    if category is None:
        raise TypeError("Выберите активную категорию")
    old = place.category_id
    source_value = str(conflict.details.get("source_value") or place.category)
    place.category_id, place.category, place.canonical_category = category.id, category.code, category.code
    if data.get("create_mapping") or data["action"] == "create_mapping":
        db.add(TaxonomyMapping(source=conflict.source or "legacy",
            source_key=str(conflict.details.get("source_key") or "legacy_category"),
            source_value=source_value, target_category_id=category.id, priority=200, confidence=1,
            conditions={}, conditions_hash="-", created_by=actor, comment=data.get("comment")))
    result = classify_place(db, source=None, source_tags={}, title=place.title,
                            description=place.short_description, current_category=place.category,
                            manual_category_id=category.id)
    persist_decision(db, place_id=place.id, result=result, actor=actor, old_category_id=old)


def _exclude_route(db: Session, place: Place, actor: str) -> None:
    try:
        reconcile_published_place_state(db, place, route_eligible=False,
            route_exclusion_reason="taxonomy_conflict_excluded", actor=actor,
            source="admin_taxonomy_conflict")
    except InvalidPublicationTransition:
        return
