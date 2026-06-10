"""
Расширение SQLAlchemy Query для текстового поиска по полям Place (список/поиск).
"""

from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place


# Добавляет текстовый поиск по месту.
def apply_place_text_search(query: Query, q: str | None) -> Query:
    """
    Добавляет текстовый поиск по полям Place.

    Пока ищем по:
    - title
    - slug

    Позже сюда можно добавить:
    - short_description
    - full_description
    - address
    """
    if not q:
        return query

    search_value = f"%{q.strip()}%"

    return query.filter(
        or_(
            Place.title.ilike(search_value),
            Place.slug.ilike(search_value),
        )
    )
