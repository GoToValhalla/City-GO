"""
Прототип AI-endpoint: прокси к services.ai_service.process_ai_query.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.ai import AIQueryRequest
from services.ai_service import process_ai_query
from services.feature_toggle_guards import assert_ai_layer

router = APIRouter(prefix="/ai", tags=["ai"])


# Тестовый endpoint для будущего AI-слоя.
@router.get("/health")
def ai_health() -> dict[str, str]:
    return {"status": "ai router ready"}


# Endpoint для приема AI-запроса.
@router.post("/query")
def ai_query(
    payload: AIQueryRequest,
    db: Session = Depends(get_db),
) -> dict:
    assert_ai_layer(db)
    return process_ai_query(
        query=payload.query,
        db=db,
        lat=payload.lat,
        lng=payload.lng,
    )
