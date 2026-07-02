from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель города.
# Нужна для масштабирования проекта на несколько городов.
# TODO(Data Foundation V2): City не должен оставаться корневой продуктовой сущностью.
# Целевая модель: City становится частным типом Destination(type='city'), а городовые поля
# сохраняются как legacy/backward-compatible слой до полной миграции каталога, импорта и маршрутов.
# Нельзя моделировать Байкал/Алтай/Карелию как fake City — для них нужны Destination/GeoZone/ImportScope.
class City(Base):
    __tablename__ = "cities"

    # Уникальный идентификатор города.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Человекочитаемый код города для URL и внутреннего использования.
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название города на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Регион, к которому относится город.
    # TODO(Data Foundation V2): разделить административный регион и туристический Destination.
    # Поле region остается legacy-текстом; целевая связь должна идти через AdminRegion/DestinationRelation.
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
    # TODO(Data Foundation V2): эти поля должны переехать/дублироваться в Destination.
    # Для city destination можно сохранить текущую bbox-логику; для natural_region/national_park
    # нужны real boundary / OSM relation / manual polygon / tiled import scopes.
    osm_relation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    boundary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Координаты центра города.
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    launch_status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft", index=True)
    slug_aliases: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Data Foundation city-level quality metadata.
    # TODO(Data Foundation V2): readiness/quality должны считаться по Destination и ImportScope,
    # иначе большой регион нельзя публиковать поэтапно и оценивать по кластерам.
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_ready", index=True)
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_import_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    population_tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    expected_places_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Признак активности города в публичной витрине.
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

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


_PUBLICATION_GUARD_FLAG = "_allow_product_publication_state_change"


def allow_city_product_state_change(city: City) -> None:
    """Mark an explicit admin/repair action as allowed to change product state."""
    setattr(city, _PUBLICATION_GUARD_FLAG, True)


def _city_product_state_change_allowed(city: City) -> bool:
    return bool(getattr(city, _PUBLICATION_GUARD_FLAG, False))


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
