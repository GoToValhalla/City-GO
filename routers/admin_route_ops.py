"""Admin: dry-run и диагностика маршрутов."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_route_dry_run import AdminRouteDryRunRequest, AdminRouteDryRunResponse
from services.admin_route_dry_run_service import AdminRouteDryRunService

router = APIRouter(prefix="/admin/routes", tags=["admin-routes"])


@router.post("/dry-run", response_model=AdminRouteDryRunResponse)
def post_admin_route_dry_run(
    payload: AdminRouteDryRunRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteDryRunResponse:
    return AdminRouteDryRunService().run(db, request=payload, actor_id=auth.actor_id)
