from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_seed_import_request import PlaceSeedImportRequest
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from services.place_seed_import_service import import_place_seed_items

router = APIRouter(
    prefix="/place-seed/import",
    tags=["place-seed-import"],
)


@router.post("/", response_model=PlaceSeedImportSummary)
def import_place_seed_payload(
    payload: PlaceSeedImportRequest,
    db: Session = Depends(get_db),
) -> PlaceSeedImportSummary:
    return import_place_seed_items(db, payload.items, dry_run=payload.dry_run)
