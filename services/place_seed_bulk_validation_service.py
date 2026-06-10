"""
Пакетная валидация seed-мест: агрегирует результаты поэлементной проверки.
"""

from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_item import PlaceSeedItem
from services.place_seed_validation_service import validate_place_seed_item


def validate_place_seed_items(
    items: list[PlaceSeedItem],
) -> PlaceSeedBulkValidationResponse:
    """
    Валидирует список seed-элементов мест и собирает общий результат.
    """
    results = [validate_place_seed_item(item) for item in items]

    valid_count = sum(1 for item in results if item.is_valid)
    invalid_count = len(results) - valid_count

    return PlaceSeedBulkValidationResponse(
        total=len(results),
        valid_count=valid_count,
        invalid_count=invalid_count,
        items=results,
    )
