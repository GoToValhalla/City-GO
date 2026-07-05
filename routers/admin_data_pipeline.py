"""Read-only Data Pipeline Control Plane endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.data_pipeline_status import DataPipelineStatusResponse
from services.data_pipeline_status.build_status import build_data_pipeline_status

router = APIRouter(prefix="/admin/data-pipeline", tags=["admin-data-pipeline"])


@router.get("/status", response_model=DataPipelineStatusResponse)
def read_data_pipeline_status(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DataPipelineStatusResponse:
    return build_data_pipeline_status(db)
