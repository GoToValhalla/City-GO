"""
Применение сортировки к ORM-запросу списка мест (whitelist полей из SortingParams).
"""

from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

from models.place import Place
from schemas.sorting import SortingParams
from services.sorting_service import normalize_sorting_params


def apply_place_sorting(query: Query, params: SortingParams) -> Query:
    """
    Применяет сортировку к query мест.

    Поддерживаемые поля:
    - title
    - created_at
    """
    normalized = normalize_sorting_params(params)

    sort_fields = {
        "title": Place.title,
        "created_at": Place.created_at,
    }

    column = sort_fields[normalized.sort_by]
    order_func = asc if normalized.sort_order == "asc" else desc

    return query.order_by(order_func(column))
