"""
Справочник тегов мест.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.tag import TagRead
from services.tag_service import get_tag_by_code, get_tag_by_id, get_tags

router = APIRouter(prefix="/tags", tags=["tags"])


# Возвращает список всех тегов из базы.
@router.get("/", response_model=list[TagRead])
def read_tags(db: Session = Depends(get_db)) -> list[TagRead]:
    return get_tags(db)


# Возвращает один тег по идентификатору.
@router.get("/{tag_id}", response_model=TagRead)
def read_tag(tag_id: int, db: Session = Depends(get_db)) -> TagRead:
    tag = get_tag_by_id(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


# Возвращает один тег по коду.
@router.get("/by-code/{code}", response_model=TagRead)
def read_tag_by_code(code: str, db: Session = Depends(get_db)) -> TagRead:
    tag = get_tag_by_code(db, code)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag
