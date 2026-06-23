from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Place(Base):
    __tablename__ = "places"
    __table_args__ = (
        # Slug должен быть уникален внутри города, а не глобально: "central-park" есть в десятках городов.
        # TODO(Data Foundation V2): после ввода Destination slug uniqueness должен стать context-aware:
        # legacy city uniqueness сохраняется, но целевой контекст — primary_destination/place_destinations.
        UniqueConstraint("city_id", "slug", name="uq_places_city_id_slug"),
        CheckConstraint("quality_score >= 0 AND quality_score <= 100", name="ck_places_quality_score_range"),
        CheckConstraint("completeness_score >= 0 AND completeness_score <= 40", name="ck_places_completeness_score_range"),
        CheckConstraint("photo_score >= 0 AND photo_score <= 25", name="ck_places_photo_score_range"),
        CheckConstraint("description_score >= 0 AND description_score <= 15", name="ck_places_description_score_range"),
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 10", name="ck_places_confidence_score_range"),
        CheckConstraint("freshness_score >= 0 AND freshness_score <= 10", name="ck_places_freshness_score_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # TODO(Data Foundation V2): city_id остается legacy/backward-compatible FK.
    # Целевая модель: Place должен быть геонезависимым объектом с координатами, primary_destination_id
    # и many-to-many связью PlaceDestination. Байкал/Алтай/Карелия не должны требовать fake city_id.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)

    slug: Mapped[str] = mapped_column(String, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    address_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    address_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    route_exclusion_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    admin_comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    # Data Foundation contract. Legacy fields remain intact, but new logic must use these canonical fields.
    canonical_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    quality_tier: Mapped[str] = mapped_column(String(32), default="silver", nullable=False, index=True)
    quality_score: Mapped[int] = mapped_column(Integer, default=65, nullable=False, index=True)
    completeness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    photo_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    freshness_score: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_spam_poi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_duplicate_suspected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    geo_precision: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    critical_field_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    existence_confidence_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    existence_confidence_level: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified", index=True)
    verification_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    needs_recheck_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Новые импортированные и вручную созданные места безопасно остаются draft.
    # Публикация выполняется отдельным admin-действием после quality gate города.
    # TODO(Data Foundation V2): публикация должна стать context-aware: Place может быть опубликован
    # в одном Destination и скрыт в другом. Для больших регионов нужен staged tier publication.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_visible_in_catalog: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_route_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    publication_status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    publication_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    unpublished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # TODO(Data Foundation V2): добавить PostGIS geometry(Point, 4326) / geography индекс.
    # lat/lng оставить для backward compatibility и SQLite-тестов, но spatial membership
    # PlaceDestination должен считаться через геометрию/полигон/corridor, а не через city_id.
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    outdoor: Mapped[bool] = mapped_column(Boolean, default=False)
    indoor: Mapped[bool] = mapped_column(Boolean, default=False)
    dog_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    family_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    price_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_hours: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    average_visit_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda ctx: ctx.get_current_parameters().get("created_at") or datetime.utcnow(),
        onupdate=datetime.utcnow,
    )

    city = relationship("City", back_populates="places")
    category_ref = relationship("Category", back_populates="places")
    route_places = relationship("RoutePlace", back_populates="place")
    collection_places = relationship("CollectionPlace", back_populates="place")
    place_tags = relationship("PlaceTag", back_populates="place")
    schedules = relationship("PlaceSchedule", back_populates="place")
    images = relationship("PlaceImage", back_populates="place")
    field_provenance = relationship("PlaceFieldProvenance", back_populates="place")
    state_transitions = relationship("PlaceStateTransition", back_populates="place")
    quality_history = relationship("QualityScoreHistory", back_populates="place")


@event.listens_for(Place, "before_insert")
def set_place_insert_timestamps(mapper: object, connection: object, target: Place) -> None:
    timestamp = target.created_at or target.updated_at or datetime.utcnow()
    target.created_at = target.created_at or timestamp
    target.updated_at = target.updated_at or timestamp
