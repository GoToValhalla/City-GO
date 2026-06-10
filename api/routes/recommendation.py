from fastapi import APIRouter

from app.schemas.request import RecommendationRequest
from app.services.pipeline import RecommendationPipeline

router = APIRouter()
pipeline = RecommendationPipeline()


@router.post("/recommend")
def recommend(request: RecommendationRequest):
    """
    Главная ручка рекомендаций

    Принимает:
    - session context (минимум)
    
    Возвращает:
    - маршрут (пока сырой, без форматирования под UI)
    """

    route = pipeline.run(request)

    return {
        "status": "ok",
        "route": route
    }
