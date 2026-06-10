"""
Список мест «открыто сейчас» по городу (расписание в БД).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.open_now import OpenNowPlaceRead
from services.open_now_service import get_open_now_places

router = APIRouter(prefix="/open-now", tags=["open-now"])


# Возвращает список мест, которые открыты сейчас в выбранном городе.
@router.get("/", response_model=list[OpenNowPlaceRead])
def read_open_now_places(
    city_slug: str = Query(...),
    db: Session = Depends(get_db),
) -> list[OpenNowPlaceRead]:
    return get_open_now_places(
        db=db,
        city_slug=city_slug,
    )
