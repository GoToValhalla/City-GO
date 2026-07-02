from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SourceObservation(Base):
    """Append-only raw provider observation.

    Stage 1 data foundation contract: ingestion writes raw observations, not public catalog state.
    """

    __tablename__ = "source_observations"
    __table_args__ = (
        UniqueConstraint("source_type", "source_external_id", name="uq_source_observation_provider_object"),
        UniqueConstraint("idempotency_key", name="uq_source_observation_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    scope_id: Mapped[int | None] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="osm", index=True)
    source_external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_object_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_license: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    attribution_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    raw_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=dict)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    seen_in_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    canonical_place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    match_status: Mapped[str] = mapped_column(String(64), nullable=False, default="new_source_object")
    normalization_status: Mapped[str] = mapped_column(String(64), nullable=False, default="raw_only")
    rejection_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
