from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class CityCandidate(Base):
    __tablename__ = "city_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False, index=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="city")
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    osm_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    wikidata_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geonames_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="candidate", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    city_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
