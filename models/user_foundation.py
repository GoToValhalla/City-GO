"""Dark-launch user/account/review foundation models.

These models are additive only and intentionally isolated from public city/place/route
read paths. They are not imported by public query services and must remain inert while
all user-foundation feature flags are OFF.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


UUID_LEN = 36
SUBJECT_TYPE_LEN = 32
STATUS_LEN = 32
PROVIDER_LEN = 32


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('active', 'deleted', 'blocked')", name="ck_users_status"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class AnonymousIdentity(Base):
    __tablename__ = "anonymous_identities"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    device_id_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject_hash", name="uq_external_identity_provider_subject_hash"),
        CheckConstraint("status IN ('active', 'revoked', 'conflict', 'deleted')", name="ck_external_identities_status"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(PROVIDER_LEN), nullable=False, index=True)
    provider_subject_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_subject_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)


class TelegramIdentity(Base):
    __tablename__ = "telegram_identities"
    __table_args__ = (CheckConstraint("status IN ('active', 'revoked', 'conflict', 'deleted')", name="ck_telegram_identities_status"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    telegram_user_id_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    telegram_user_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_chat_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    username_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notifications_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocked_bot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="active", index=True)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)


class IdentityLinkEvent(Base):
    __tablename__ = "identity_link_events"
    __table_args__ = (CheckConstraint("status IN ('pending', 'linked', 'rejected', 'conflict', 'expired')", name="ck_identity_link_events_status"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    from_identity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_identity_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    to_identity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    to_identity_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "key", name="uq_user_preferences_subject_key"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class FavoritePlace(Base):
    __tablename__ = "favorite_places"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class SavedRoute(Base):
    __tablename__ = "saved_routes"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    route_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    source_route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class RouteHistory(Base):
    __tablename__ = "route_history"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    route_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    stats_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_reviews_rating_1_5"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'hidden', 'spam', 'duplicate', 'needs_more_info')",
            name="ck_reviews_status",
        ),
        UniqueConstraint("client_generated_id", name="uq_reviews_client_generated_id"),
    )

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    lang: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    client_generated_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ReviewVote(Base):
    __tablename__ = "review_votes"
    __table_args__ = (CheckConstraint("value IN (-1, 1)", name="ck_review_votes_value"),)

    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id"), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class PlaceRatingAggregate(Base):
    __tablename__ = "place_rating_aggregates"

    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), primary_key=True)
    approved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_avg: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    rating_histogram_json: Mapped[dict[str, int] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserPhoto(Base):
    __tablename__ = "user_photos"
    __table_args__ = (CheckConstraint("status IN ('pending', 'approved', 'rejected', 'hidden', 'spam')", name="ck_user_photos_status"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    subject_type: Mapped[str] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    storage_ref: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    license_status: Mapped[str] = mapped_column(String(32), nullable=False, default="REVIEW", index=True)
    exif_stripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserSuggestion(Base):
    __tablename__ = "user_suggestions"
    __table_args__ = (CheckConstraint("kind IN ('new_place', 'edit_place', 'report_problem')", name="ck_user_suggestions_kind"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(UUID_LEN), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    client_generated_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModerationItem(Base):
    __tablename__ = "moderation_items"
    __table_args__ = (UniqueConstraint("kind", "ref_id", name="uq_moderation_items_kind_ref"),)

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ref_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    priority: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class AbuseReport(Base):
    __tablename__ = "abuse_reports"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(UUID_LEN), nullable=False, index=True)
    subject_type: Mapped[str | None] = mapped_column(String(SUBJECT_TYPE_LEN), nullable=True, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(UUID_LEN), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(STATUS_LEN), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserFoundationAuditLog(Base):
    __tablename__ = "user_foundation_audit_logs"

    id: Mapped[str] = mapped_column(String(UUID_LEN), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(UUID_LEN), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str | None] = mapped_column(String(UUID_LEN), nullable=True, index=True)
    payload_json: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
