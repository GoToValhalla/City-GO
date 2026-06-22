from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.start_point import ResolveStartRequest, ResolveStartResponse
from services.start_point_service import resolve_start

router = APIRouter(prefix="/geo", tags=["geo"])


@router.post("/resolve-start", response_model=ResolveStartResponse)
def resolve_route_start(payload: ResolveStartRequest, db: Session = Depends(get_db)) -> ResolveStartResponse:
    result = resolve_start(db, payload)
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "CITY_NOT_FOUND", "message": "City not found"})
    return ResolveStartResponse(**result)


@router.post("/resolve-address", response_model=ResolveStartResponse)
def resolve_route_address(payload: ResolveStartRequest, db: Session = Depends(get_db)) -> ResolveStartResponse:
    return resolve_route_start(payload, db)
