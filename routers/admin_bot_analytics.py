from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.admin_bot_analytics_service import get_bot_analytics_summary

router = APIRouter(prefix="/admin/telegram-bot", tags=["admin-telegram-bot"])


@router.get("/analytics")
def get_telegram_bot_analytics(
    days: int = Query(7, ge=1, le=90),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_bot_analytics_summary(db, days=days)
