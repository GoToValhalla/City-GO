"""LEGACY/SCOPE SCHEDULER MODEL.

This table belongs to the old import-scope cron foundation. It is not the source
of truth for the admin import monitor, latest import status, or dashboard import
state.

Active admin import source of truth:
- `models.city_admin_import_job.CityAdminImportJob`
- table `city_admin_import_jobs`
- admin import job services/runners.

Rules:
- Do not use this model for admin latest import status.
- Do not use this model to change `City.is_active` or `City.launch_status`.
- Keep it for historical scope scheduler compatibility until a dedicated import
  storage consolidation task migrates old jobs safely.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityImportJob(Base):
    __tablename__ = "city_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    scope_id: Mapped[int] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="incremental_refresh")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending", index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
