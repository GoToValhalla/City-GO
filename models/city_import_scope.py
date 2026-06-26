from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityImportScope(Base):
    __tablename__ = "city_import_scopes"

    # TODO(Data Foundation V2): CityImportScope должен стать DestinationImportScope.
    # Текущая city_id/bbox модель подходит для компактного города, но не для Байкала/Алтая/Карелии.
    # Целевой scope должен поддерживать destination_id, strategy, polygon, osm_relation, tiling,
    # route_corridor buffer и per-child import для туристических кластеров.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # TODO(Data Foundation V2): bbox остается legacy strategy=single_bbox.
    # Для больших территорий нельзя использовать один огромный bbox — нужен tiled/manual_polygon/osm_relation.
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    polygon: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft", index=True)

    # New import scopes must participate in refresh pipelines by default. To stop an
    # import scope, set status='paused' explicitly; enabled=False remains only a
    # legacy/manual kill switch for old data and is repaired by the refresh workflow.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # TODO(Data Foundation V2): import_profile должен зависеть от DestinationType:
    # city_tourist / nature_region / national_park / route_corridor / tourist_cluster.
    # Utility-профили должны быть отделены от туристического каталога и маршрутов.
    import_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="tourist_core")
    coverage_targets: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    refresh_interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
