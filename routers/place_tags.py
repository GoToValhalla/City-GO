"""
Связи place ↔ tag для фильтрации и админки.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_tag import PlaceTagRead
from services.place_tag_service import get_place_tags, get_place_tags_by_place_id

router = APIRouter(prefix="/place-tags", tags=["place-tags"])


# Возвращает список всех связей мест и тегов.
# Если передан place_id, возвращает связи только для выбранного места.
@router.get("/", response_model=list[PlaceTagRead])
def read_place_tags(
    place_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PlaceTagRead]:
    if place_id is not None:
        return get_place_tags_by_place_id(db, place_id)
    return get_place_tags(db)
