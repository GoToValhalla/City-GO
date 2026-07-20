from fastapi import APIRouter, Depends

from core.admin_auth import AdminContext, admin_required
from schemas.place_seed_bulk_validation_response import PlaceSeedBulkValidationResponse
from schemas.place_seed_validation_request import PlaceSeedValidationRequest
from services.place_seed_bulk_validation_service import validate_place_seed_items

router = APIRouter(
    prefix="/place-seed/validate",
    tags=["place-seed-validation"],
)


@router.post("/", response_model=PlaceSeedBulkValidationResponse)
def validate_place_seed_payload(
    payload: PlaceSeedValidationRequest,
    auth: AdminContext = Depends(admin_required),
) -> PlaceSeedBulkValidationResponse:
    del auth
    return validate_place_seed_items(payload.items)
