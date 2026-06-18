from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель города.
# Нужна для масштабирования проекта на несколько городов.
class City(Base):
    __tablename__ = "cities"

    # Уникальный идентификатор города.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Человекочитаемый код города для URL и внутреннего использования.
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название города на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Регион, к которому относится город.
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Страна.
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Россия")

    country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id"), nullable=True, index=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True, index=True)
    city_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("city_candidates.id"), nullable=True)

    # Часовой пояс города. Нужен для корректного "открыто сейчас" и freshness checks.
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="Europe/Kaliningrad")

    # Языковая метаинформация нужна для enrichment, AI-описаний и локализации витрины.
    primary_language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru", index=True)
    secondary_languages: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Внешняя идентификация города и границы импорта.
    osm_relation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    boundary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Координаты центра города.
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    launch_status: Mapped[str] = mapped_column(String(64), nullable=False, default="published", index=True)
    slug_aliases: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Data Foundation city-level quality metadata.
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_ready", index=True)
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    population_tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    expected_places_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Признак активности города.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь города с местами.
    places = relationship("Place", back_populates="city")

    # Связь города с подборками.
    collections = relationship("Collection", back_populates="city")

    # Связь города с маршрутами.
    routes = relationship("Route", back_populates="city")

    # Связь города со снапшотами качества и enrichment runs.
    quality_snapshots = relationship("CityQualitySnapshot", back_populates="city")
    enrichment_runs = relationship("CityEnrichmentRun", back_populates="city")
