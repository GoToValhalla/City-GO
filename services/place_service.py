"""
Сборка списка мест: нормализация параметров, фильтры, сортировка, пагинация и total.
"""

from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceCreate, PlaceUpdate
from schemas.place_query_params import PlaceQueryParams
from services.place_count_service import get_query_total
from services.place_filters_service import apply_place_filters
from services.place_public_visibility import apply_public_place_visibility
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
    destination_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    sort_order: str = "asc",
    public_only: bool = True,
) -> list[Place]:
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            destination_slug=destination_slug,
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
    if public_only:
        query = apply_public_place_visibility(query)

    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        destination_slug=params.destination_slug,
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
    destination_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    public_only: bool = True,
) -> int:
    """Возвращает общее количество мест по тем же фильтрам, но без limit / offset."""
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            destination_slug=destination_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
        )
    )

    query = db.query(Place)
    if public_only:
        query = apply_public_place_visibility(query)
    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        destination_slug=params.destination_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return 0

    query = apply_place_text_search(query, params.q)
    return get_query_total(query)


# Возвращает одно место по его идентификатору.
def get_place_by_id(db: Session, place_id: int, *, public_only: bool = False) -> Place | None:
    query = db.query(Place).filter(Place.id == place_id)
    if public_only:
        query = apply_public_place_visibility(query)
    return query.first()


# Возвращает одно место по его slug.
def get_place_by_slug(db: Session, slug: str, *, public_only: bool = False) -> Place | None:
    query = db.query(Place).filter(Place.slug == slug)
    if public_only:
        query = apply_public_place_visibility(query)
    return query.first()


# Создает новое место, сохраняет его в базе и возвращает результат.
def create_place(db: Session, place_in: PlaceCreate) -> Place:
    place = Place(**_place_column_payload(place_in.model_dump()))
    db.add(place)
    db.commit()
    db.refresh(place)
    _shadow_write_membership(db, place)
    return place


def _shadow_write_membership(db: Session, place: Place) -> None:
    from models.city import City
    from services.city_destination_compatibility import get_destination_for_city
    from services.destination_flags import destination_import_enabled
    from services.destination_membership_service import upsert_membership

    city = db.query(City).filter(City.id == place.city_id).first()
    if city is None:
        return
    dest = get_destination_for_city(db, city)
    if dest is None:
        return
    upsert_membership(
        db,
        place_id=place.id,
        destination_id=dest.id,
        assignment_type="legacy_city" if not destination_import_enabled() else "imported",
        is_primary=True,
        source="place_write_shadow",
    )
    if place.primary_destination_id is None:
        place.primary_destination_id = dest.id
    db.commit()


# Обновляет существующее место и возвращает его после сохранения.
def update_place(db: Session, place_id: int, place_in: PlaceUpdate) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None

    for field, value in _place_column_payload(place_in.model_dump()).items():
        setattr(place, field, value)

    if place_in.lat is not None or place_in.lng is not None:
        from services.destination_membership_service import mark_place_stale

        mark_place_stale(db, place.id)

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
