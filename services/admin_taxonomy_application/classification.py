from __future__ import annotations

from sqlalchemy.orm import Session

from models.category import Category
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.taxonomy_rule_engine import classify_place, persist_decision


def preview_classification(db: Session, data: dict[str, object]) -> dict[str, object]:
    data.pop("place_id", None)
    return classify_place(db, **data).to_dict()


def apply_classification(db: Session, data: dict[str, object], *, actor: str) -> dict[str, object]:
    place_id = data.pop("place_id", None)
    expected = data.pop("expected_category_id", None)
    if place_id is None:
        raise TypeError("Для применения требуется place_id")
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise LookupError("Место не найдено")
    result = classify_place(db, **data)
    if result.decision not in {"auto_apply", "manual"}:
        raise ValueError("Низкоуверенную классификацию нельзя применить без ручного выбора")
    if expected is not None and place.category_id != expected:
        raise ValueError("Категория места изменилась после preview")
    category = db.query(Category).filter(Category.id == result.category_id, Category.is_active.is_(True)).first()
    if category is None:
        raise ValueError("Рекомендованная категория недоступна")
    old = place.category_id
    place.category_id, place.category, place.canonical_category = category.id, category.code, category.code
    persist_decision(db, place_id=place.id, result=result, actor=actor, old_category_id=old)
    write_admin_audit_log(db, actor=actor, action="taxonomy.classification.applied",
                          entity_type="place", entity_id=place.id,
                          old_value={"category_id": old},
                          new_value={"category_id": category.id, "explanation": result.explanation})
    db.commit()
    return {**result.to_dict(), "applied": True}
