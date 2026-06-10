"""
Справочник категорий мест (read-only).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.category import CategoryRead
from services.category_service import (
    get_categories,
    get_category_by_code,
    get_category_by_id,
)

router = APIRouter(prefix="/categories", tags=["categories"])


# Возвращает список всех категорий из базы.
@router.get("/", response_model=list[CategoryRead])
def read_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return get_categories(db)


# Возвращает одну категорию по идентификатору.
@router.get("/{category_id}", response_model=CategoryRead)
def read_category(category_id: int, db: Session = Depends(get_db)) -> CategoryRead:
    category = get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# Возвращает одну категорию по коду.
@router.get("/by-code/{code}", response_model=CategoryRead)
def read_category_by_code(code: str, db: Session = Depends(get_db)) -> CategoryRead:
    category = get_category_by_code(db, code)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
