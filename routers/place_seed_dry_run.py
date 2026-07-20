from fastapi import APIRouter, Depends

from core.admin_auth import AdminContext, admin_required
from schemas.place_seed_dry_run_request import PlaceSeedDryRunRequest
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from services.place_seed_dry_run_service import run_place_seed_dry_run

router = APIRouter(
    prefix="/place-seed/dry-run",
    tags=["place-seed-dry-run"],
)


@router.post("/", response_model=PlaceSeedImportSummary)
def dry_run_place_seed_payload(
    payload: PlaceSeedDryRunRequest,
    auth: AdminContext = Depends(admin_required),
) -> PlaceSeedImportSummary:
    del auth
    return run_place_seed_dry_run(payload.items)
