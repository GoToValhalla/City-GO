from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_import_log import PlaceImportLogSummary
from services.place_import_log_service import place_import_summary

router = APIRouter(prefix="/place-import-logs", tags=["place-import-logs"])


@router.get("/summary", response_model=PlaceImportLogSummary)
def get_place_import_log_summary(db: Session = Depends(get_db)) -> PlaceImportLogSummary:
    return PlaceImportLogSummary.model_validate(place_import_summary(db))
