"""
Диагностика: какие значения из payload не входят в канон таксономии.
"""

from fastapi import APIRouter

from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)

router = APIRouter(
    prefix="/place-taxonomy/diagnostics",
    tags=["place-taxonomy-diagnostics"],
)


@router.post("/", response_model=PlaceTaxonomyDiagnosticsResponse)
def validate_place_taxonomy_payload(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Проверяет taxonomy payload и возвращает только невалидные значения.

    Нужен для:
    - seed-данных
    - импорта
    - AI enrichment pipeline
    - ручной проверки payload перед записью
    """
    return get_invalid_place_taxonomy_values(payload)