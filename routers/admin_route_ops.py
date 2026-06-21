"""Admin: dry-run и диагностика маршрутов."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_route_dry_run import AdminRouteDryRunRequest, AdminRouteDryRunResponse
from services.admin_route_dry_run_service import AdminRouteDryRunService
from services.route_pipeline_trace import get_last_route_debug

router = APIRouter(prefix="/admin/routes", tags=["admin-routes"])


@router.post("/dry-run", response_model=AdminRouteDryRunResponse)
def post_admin_route_dry_run(
    payload: AdminRouteDryRunRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminRouteDryRunResponse:
    return AdminRouteDryRunService().run(db, request=payload, actor_id=auth.actor_id)


@router.get("/debug-last")
def get_admin_route_debug_last(
    auth: AdminContext = Depends(admin_required),
) -> dict[str, Any]:
    debug = get_last_route_debug()
    return debug or {
        "route_id": None,
        "summary": {},
        "compact_trace": [],
        "full_trace": [],
        "message": "No route debug has been recorded in this backend process yet.",
    }
