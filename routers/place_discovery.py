from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_discovery import PlaceDiscoveryCreate, PlaceDiscoveryRead
from services.place_discovery_service import create_discovery_request

router = APIRouter(prefix="/place-discovery", tags=["place-discovery"])


@router.post("/", response_model=PlaceDiscoveryRead)
def post_discovery(payload: PlaceDiscoveryCreate, db: Session = Depends(get_db)) -> PlaceDiscoveryRead:
    try:
        return create_discovery_request(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
