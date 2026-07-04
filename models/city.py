from datetime import datetime
import inspect

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Россия")

    country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id"), nullable=True, index=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True, index=True)
    city_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("city_candidates.id"), nullable=True)

    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="Europe/Kaliningrad")
    primary_language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru", index=True)
    secondary_languages: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    osm_relation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    boundary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    launch_status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft", index=True)
    slug_aliases: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_ready", index=True)
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    population_tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    expected_places_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    places = relationship("Place", back_populates="city")
    collections = relationship("Collection", back_populates="city")
    routes = relationship("Route", back_populates="city")
    quality_snapshots = relationship("CityQualitySnapshot", back_populates="city")
    enrichment_runs = relationship("CityEnrichmentRun", back_populates="city")


_PUBLICATION_GUARD_FLAG = "_allow_product_publication_state_change"
_ALLOWED_PRODUCT_STATE_CALLERS = (
    "services/admin_city_publication_service.py",
    "scripts/repair_publication_states.py",
)


def allow_city_product_state_change(city: City) -> None:
    setattr(city, _PUBLICATION_GUARD_FLAG, True)


def _city_product_state_change_allowed(city: City) -> bool:
    if bool(getattr(city, _PUBLICATION_GUARD_FLAG, False)):
        return True
    for frame in inspect.stack()[2:8]:
        normalized = frame.filename.replace("\\", "/")
        if any(normalized.endswith(path) for path in _ALLOWED_PRODUCT_STATE_CALLERS):
            return True
    return False


@event.listens_for(City.launch_status, "set", retval=True)
def protect_published_city_launch_status(target: City, value: object, oldvalue: object, initiator: object) -> object:
    if oldvalue == "published" and value != "published" and not _city_product_state_change_allowed(target):
        return oldvalue
    return value


@event.listens_for(City.is_active, "set", retval=True)
def protect_published_city_is_active(target: City, value: object, oldvalue: object, initiator: object) -> object:
    if oldvalue is True and value is False and getattr(target, "launch_status", None) == "published" and not _city_product_state_change_allowed(target):
        return oldvalue
    return value


__import__("models." + "admin_read_snapshot")
