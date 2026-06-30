from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.admin_city_import_tasks import import_queue_summary

router = APIRouter(prefix="/admin", tags=["admin-import-queue"])


@router.get("/import-queue")
def read_import_queue(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    return import_queue_summary(db)
