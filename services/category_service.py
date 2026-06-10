"""
CRUD-чтение справочника категорий мест (таблица categories).
"""

from sqlalchemy.orm import Session

from models.category import Category


# Возвращает список всех категорий из базы данных.
def get_categories(db: Session) -> list[Category]:
    return db.query(Category).all()


# Возвращает одну категорию по ее идентификатору.
def get_category_by_id(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


# Возвращает одну категорию по ее коду.
def get_category_by_code(db: Session, code: str) -> Category | None:
    return db.query(Category).filter(Category.code == code).first()
