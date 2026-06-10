"""
Нормализация limit/offset для пагинации API (дефолты и лимиты — здесь при росте проекта).
"""

from schemas.pagination import PaginationParams


def normalize_pagination_params(params: PaginationParams) -> PaginationParams:
    """
    Нормализует параметры пагинации.

    Пока это просто единая точка входа.
    Позже сюда можно добавить:
    - project-wide defaults
    - max-limit rules by endpoint
    - soft caps
    """
    return PaginationParams(
        limit=params.limit,
        offset=params.offset,
    )
