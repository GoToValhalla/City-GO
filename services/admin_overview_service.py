"""Admin overview actionable cards."""

from __future__ import annotations

from sqlalchemy.orm import Session


def build_admin_overview(db: Session) -> dict[str, object]:
    try:
        from services.admin_read_model_v2 import admin_overview

        return admin_overview(db)
    except Exception:
        from services.admin_overview_compact import build_admin_overview as build_compact_overview

        return build_compact_overview(db)


__all__ = ["build_admin_overview"]
