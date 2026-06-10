"""
Валидация массива seed-мест против таксономии и бизнес-правил.
"""

from fastapi import APIRouter

from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_validation_request import PlaceSeedValidationRequest
from services.place_seed_bulk_validation_service import validate_place_seed_items

router = APIRouter(
    prefix="/place-seed/validate",
    tags=["place-seed-validation"],
)


@router.post("/", response_model=PlaceSeedBulkValidationResponse)
def validate_place_seed_payload(
    payload: PlaceSeedValidationRequest,
) -> PlaceSeedBulkValidationResponse:
    """
    Валидирует список seed-элементов мест и возвращает общий результат.

    Нужен для:
    - bulk seed import
    - ручной проверки seed-файлов
    - AI enrichment pipeline
    - pre-ingest validation
    """
    return validate_place_seed_items(payload.items)