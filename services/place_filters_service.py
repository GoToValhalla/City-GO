"""
Фильтры списка Place: публичная видимость, город (id/slug), категория, тег (join place_tags).
"""

from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from models.place_tag import PlaceTag
from services.place_public_visibility import apply_public_place_visibility

PUBLISHED_CITY_STATUS = "published"


def apply_place_filters(
    db: Session,
    query: Query,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
) -> Query | None:
    """
    Применяет базовые публичные фильтры к query мест.

    Возвращает:
    - Query, если фильтры применены успешно
    - None, если city_slug передан, но опубликованный город не найден
    """
    # Публичные места доступны только внутри опубликованных городов.
    # Иначе импортированный, но не проверенный город можно открыть прямым city_slug.
    query = query.join(City, Place.city_id == City.id).filter(
        City.is_active.is_(True),
        City.launch_status == PUBLISHED_CITY_STATUS,
    )

    # Сначала применяем единый фильтр публичной видимости:
    # active + is_active + без временно скрытых категорий.
    query = apply_public_place_visibility(query)

    # Фильтруем по городу через city_id.
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)

    # Фильтруем по городу через city_slug.
    if city_slug is not None:
        city = db.query(City).filter(
            City.slug == city_slug,
            City.is_active.is_(True),
            City.launch_status == PUBLISHED_CITY_STATUS,
        ).first()
        if city is None:
            return None
        query = query.filter(Place.city_id == city.id)

    # Фильтруем по категории.
    if category_id is not None:
        query = query.filter(Place.category_id == category_id)

    # Фильтруем по тегу через таблицу связей.
    if tag_id is not None:
        query = query.join(PlaceTag, Place.id == PlaceTag.place_id).filter(
            PlaceTag.tag_id == tag_id
        )

    return query