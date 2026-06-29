from fastapi import APIRouter

router = APIRouter(prefix="/navigation-events", tags=["navigation-events"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
