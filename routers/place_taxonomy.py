"""
Отдача каноничной таксономии категорий/тегов для форм и сидов.
"""

from fastapi import APIRouter

from schemas.place_taxonomy_response import PlaceTaxonomyResponse
from services.place_taxonomy_response_service import build_place_taxonomy_response

router = APIRouter(prefix="/place-taxonomy", tags=["place-taxonomy"])


@router.get("/", response_model=PlaceTaxonomyResponse)
def read_place_taxonomy() -> PlaceTaxonomyResponse:
    """
    Возвращает каноничную таксономию City GO.

    Нужна для:
    - seed-данных
    - frontend filters
    - Telegram bot
    - AI / recommendation layer
    """
    return build_place_taxonomy_response()