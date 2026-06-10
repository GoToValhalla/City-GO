"""
Сборка списка мест: нормализация параметров, фильтры, сортировка, пагинация и total.
"""

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceCreate, PlaceUpdate
from schemas.place_query_params import PlaceQueryParams
from services.place_count_service import get_query_total
from services.place_filters_service import apply_place_filters
from services.place_query_params_service import normalize_place_query_params
from services.place_search_service import apply_place_text_search
from services.place_sorting_service import apply_place_sorting


def _place_column_payload(payload: dict) -> dict:
    """Оставляет только реальные ORM-колонки Place.

    PlaceRead содержит дополнительные UI-поля изображения, которые собираются
    из PlaceImage и не должны попадать в constructor/update модели Place.
    """
    allowed_fields = {column.name for column in Place.__table__.columns}
    return {key: value for key, value in payload.items() if key in allowed_fields}


# Возвращает список мест с учетом переданных фильтров.
def get_places(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    sort_order: str = "asc",
) -> list[Place]:
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )

    query = db.query(Place)

    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return []

    query = apply_place_text_search(query, params.q)
    query = apply_place_sorting(query=query, params=params)
    query = query.offset(params.offset).limit(params.limit)

    return query.all()


def get_places_total(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
) -> int:
    """Возвращает общее количество мест по тем же фильтрам, но без limit / offset."""
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
        )
    )

    query = db.query(Place)
    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return 0

    query = apply_place_text_search(query, params.q)
    return get_query_total(query)


# Возвращает одно место по его идентификатору.
def get_place_by_id(db: Session, place_id: int) -> Place | None:
    return db.query(Place).filter(Place.id == place_id).first()


# Возвращает одно место по его slug.
def get_place_by_slug(db: Session, slug: str) -> Place | None:
    return db.query(Place).filter(Place.slug == slug).first()


# Создает новое место, сохраняет его в базе и возвращает результат.
def create_place(db: Session, place_in: PlaceCreate) -> Place:
    place = Place(**_place_column_payload(place_in.model_dump()))
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


# Обновляет существующее место и возвращает его после сохранения.
def update_place(db: Session, place_id: int, place_in: PlaceUpdate) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None

    for field, value in _place_column_payload(place_in.model_dump()).items():
        setattr(place, field, value)

    db.commit()
    db.refresh(place)
    return place


# Удаляет место по идентификатору.
def delete_place(db: Session, place_id: int) -> bool:
    place = get_place_by_id(db, place_id)
    if place is None:
        return False

    db.delete(place)
    db.commit()
    return True
