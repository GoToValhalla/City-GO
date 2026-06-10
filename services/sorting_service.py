"""
Нормализация параметров сортировки для списков (единая точка расширения правил).
"""

from schemas.sorting import SortingParams


def normalize_sorting_params(params: SortingParams) -> SortingParams:
    """
    Нормализует параметры сортировки.

    Пока это единая точка входа.
    Позже сюда можно добавить:
    - endpoint-specific defaults
    - alias mapping
    - compatibility rules
    """
    return SortingParams(
        sort_by=params.sort_by,
        sort_order=params.sort_order,
    )
