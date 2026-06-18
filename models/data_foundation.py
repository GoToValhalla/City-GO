from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class PlaceFieldProvenance(Base):
    """История происхождения конкретного поля места.

    Data Foundation требует confidence/freshness/provenance на уровне поля, а не только места.
    """

    __tablename__ = "place_field_provenance"
    __table_args__ = (
        UniqueConstraint("place_id", "field_name", "source", name="uq_place_field_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh", nullable=False, index=True)
    obtained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    is_manually_overridden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    raw_value: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    normalized_value: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    place = relationship("Place", back_populates="field_provenance")


class CityQualitySnapshot(Base):
    """Материализованный city readiness snapshot.

    Нужен, чтобы админка и route gates не считали heavy coverage-запросы каждый раз live.
    """

    __tablename__ = "city_quality_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    quality_status: Mapped[str] = mapped_column(String(32), default="not_ready", nullable=False, index=True)
    total_places_imported: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_places_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_places_route_eligible: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spam_poi_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spam_poi_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    photo_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    any_photo_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    address_full_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    address_any_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    description_any_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hours_any_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gold_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    silver_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bronze_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    draft_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rejected_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_data_age_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    stale_places_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    never_verified_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    snapshot_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    city = relationship("City", back_populates="quality_snapshots")


class CityEnrichmentRun(Base):
    """Операционный run импорта/обогащения города."""

    __tablename__ = "city_enrichment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    requested_city_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(64), default="city_enrichment", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    progress_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_done: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    city = relationship("City", back_populates="enrichment_runs")
    tasks = relationship("EnrichmentTask", back_populates="run")


class EnrichmentTask(Base):
    """Единица работы enrichment/orchestrator с retry/backoff."""

    __tablename__ = "enrichment_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("city_enrichment_runs.id"), nullable=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    run = relationship("CityEnrichmentRun", back_populates="tasks")


class PlaceStateTransition(Base):
    """Аудит lifecycle state machine для места."""

    __tablename__ = "place_state_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False, index=True)
    trigger_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    place = relationship("Place", back_populates="state_transitions")


class CanonicalCategory(Base):
    """Канонический реестр категорий Data Foundation."""

    __tablename__ = "canonical_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    is_route_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_catalog_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_spam_category: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OsmCategoryMapping(Base):
    """Явный mapping OSM tags -> canonical category без title-based эвристик."""

    __tablename__ = "osm_category_mappings"
    __table_args__ = (
        UniqueConstraint("osm_key", "osm_value", name="uq_osm_category_mapping_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    osm_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    osm_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_route_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SpamPoiRule(Base):
    """Allowlist/blocklist для инфраструктурных и мусорных POI."""

    __tablename__ = "spam_poi_rules"
    __table_args__ = (
        UniqueConstraint("source", "osm_key", "osm_value", name="uq_spam_poi_rule"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), default="osm", nullable=False, index=True)
    osm_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    osm_value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), default="block", nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class QualityScoreHistory(Base):
    """История пересчета quality score места для аудита и диагностики деградации данных."""

    __tablename__ = "quality_score_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    photo_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freshness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    place = relationship("Place", back_populates="quality_history")
