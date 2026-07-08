"""dark launch user foundation

Revision ID: b2c3d4e5f6a7
Revises: a1c2d3e4f5b6
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1c2d3e4f5b6"
branch_labels = None
depends_on = None

UUID_LEN = 36
SUBJECT_TYPE_LEN = 32
STATUS_LEN = 32


def _ts(nullable: bool = True) -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'deleted', 'blocked')", name="ck_users_status"),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    op.create_table(
        "anonymous_identities",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("device_id_hash", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(UUID_LEN), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("platform", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("device_id_hash", name="uq_anonymous_identities_device_id_hash"),
    )
    op.create_index("ix_anonymous_identities_user_id", "anonymous_identities", ["user_id"])
    op.create_index("ix_anonymous_identities_device_id_hash", "anonymous_identities", ["device_id_hash"])

    op.create_table(
        "external_identities",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("user_id", sa.String(UUID_LEN), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_subject_hash", sa.String(128), nullable=False),
        sa.Column("provider_subject_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("provider", "provider_subject_hash", name="uq_external_identity_provider_subject_hash"),
        sa.CheckConstraint("status IN ('active', 'revoked', 'conflict', 'deleted')", name="ck_external_identities_status"),
    )
    op.create_index("ix_external_identities_user_id", "external_identities", ["user_id"])
    op.create_index("ix_external_identities_provider", "external_identities", ["provider"])
    op.create_index("ix_external_identities_provider_subject_hash", "external_identities", ["provider_subject_hash"])
    op.create_index("ix_external_identities_status", "external_identities", ["status"])

    op.create_table(
        "telegram_identities",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("user_id", sa.String(UUID_LEN), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("telegram_user_id_hash", sa.String(128), nullable=False),
        sa.Column("telegram_user_id_encrypted", sa.Text(), nullable=True),
        sa.Column("telegram_chat_id_encrypted", sa.Text(), nullable=True),
        sa.Column("username_hash", sa.String(128), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notifications_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocked_bot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.UniqueConstraint("telegram_user_id_hash", name="uq_telegram_identities_user_id_hash"),
        sa.CheckConstraint("status IN ('active', 'revoked', 'conflict', 'deleted')", name="ck_telegram_identities_status"),
    )
    op.create_index("ix_telegram_identities_user_id", "telegram_identities", ["user_id"])
    op.create_index("ix_telegram_identities_telegram_user_id_hash", "telegram_identities", ["telegram_user_id_hash"])
    op.create_index("ix_telegram_identities_username_hash", "telegram_identities", ["username_hash"])
    op.create_index("ix_telegram_identities_source", "telegram_identities", ["source"])
    op.create_index("ix_telegram_identities_status", "telegram_identities", ["status"])

    op.create_table(
        "identity_link_events",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("user_id", sa.String(UUID_LEN), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("from_identity_type", sa.String(64), nullable=False),
        sa.Column("from_identity_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("to_identity_type", sa.String(64), nullable=False),
        sa.Column("to_identity_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("method", sa.String(64), nullable=False),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'linked', 'rejected', 'conflict', 'expired')", name="ck_identity_link_events_status"),
    )
    op.create_index("ix_identity_link_events_user_id", "identity_link_events", ["user_id"])
    op.create_index("ix_identity_link_events_from_identity_id", "identity_link_events", ["from_identity_id"])
    op.create_index("ix_identity_link_events_to_identity_id", "identity_link_events", ["to_identity_id"])
    op.create_index("ix_identity_link_events_method", "identity_link_events", ["method"])
    op.create_index("ix_identity_link_events_status", "identity_link_events", ["status"])
    op.create_index("ix_identity_link_events_request_id", "identity_link_events", ["request_id"])

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(UUID_LEN), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_ref", sa.String(1000), nullable=True),
        sa.Column("locale", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("subject_type", "subject_id", "key", name="uq_user_preferences_subject_key"),
    )
    op.create_index("ix_user_preferences_subject_type", "user_preferences", ["subject_type"])
    op.create_index("ix_user_preferences_subject_id", "user_preferences", ["subject_id"])
    op.create_index("ix_user_preferences_key", "user_preferences", ["key"])

    op.create_table(
        "favorite_places",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_favorite_places_subject_type", "favorite_places", ["subject_type"])
    op.create_index("ix_favorite_places_subject_id", "favorite_places", ["subject_id"])
    op.create_index("ix_favorite_places_place_id", "favorite_places", ["place_id"])
    op.create_index("ix_favorite_places_deleted_at", "favorite_places", ["deleted_at"])
    op.create_index(
        "uq_favorite_places_active_subject_place",
        "favorite_places",
        ["subject_type", "subject_id", "place_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "saved_routes",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("route_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("source_route_id", sa.Integer(), sa.ForeignKey("routes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_saved_routes_subject_type", "saved_routes", ["subject_type"])
    op.create_index("ix_saved_routes_subject_id", "saved_routes", ["subject_id"])
    op.create_index("ix_saved_routes_source_route_id", "saved_routes", ["source_route_id"])
    op.create_index("ix_saved_routes_deleted_at", "saved_routes", ["deleted_at"])

    op.create_table(
        "route_history",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("route_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_status", sa.String(64), nullable=True),
        sa.Column("stats_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_route_history_subject_type", "route_history", ["subject_type"])
    op.create_index("ix_route_history_subject_id", "route_history", ["subject_id"])
    op.create_index("ix_route_history_completion_status", "route_history", ["completion_status"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("lang", sa.String(16), nullable=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("client_generated_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("moderated_by", sa.String(255), nullable=True),
        sa.Column("rejection_reason", sa.String(1000), nullable=True),
        sa.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="ck_reviews_rating_1_5"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'hidden', 'spam', 'duplicate', 'needs_more_info')",
            name="ck_reviews_status",
        ),
        sa.UniqueConstraint("client_generated_id", name="uq_reviews_client_generated_id"),
    )
    op.create_index("ix_reviews_place_id", "reviews", ["place_id"])
    op.create_index("ix_reviews_place_status", "reviews", ["place_id", "status"])
    op.create_index("ix_reviews_subject_type", "reviews", ["subject_type"])
    op.create_index("ix_reviews_subject_id", "reviews", ["subject_id"])
    op.create_index("ix_reviews_status", "reviews", ["status"])

    op.create_table(
        "review_votes",
        sa.Column("review_id", sa.String(UUID_LEN), sa.ForeignKey("reviews.id"), primary_key=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), primary_key=True),
        sa.Column("subject_id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("value IN (-1, 1)", name="ck_review_votes_value"),
    )

    op.create_table(
        "place_rating_aggregates",
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), primary_key=True),
        sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Numeric(3, 2), nullable=True),
        sa.Column("rating_histogram_json", sa.JSON(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_photos",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=False),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("storage_ref", sa.String(1000), nullable=True),
        sa.Column("license_status", sa.String(32), nullable=False, server_default="REVIEW"),
        sa.Column("exif_stripped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'hidden', 'spam')", name="ck_user_photos_status"),
    )
    op.create_index("ix_user_photos_place_id", "user_photos", ["place_id"])
    op.create_index("ix_user_photos_subject_type", "user_photos", ["subject_type"])
    op.create_index("ix_user_photos_subject_id", "user_photos", ["subject_id"])
    op.create_index("ix_user_photos_license_status", "user_photos", ["license_status"])
    op.create_index("ix_user_photos_status", "user_photos", ["status"])

    op.create_table(
        "user_suggestions",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=True),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("client_generated_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('new_place', 'edit_place', 'report_problem')", name="ck_user_suggestions_kind"),
        sa.UniqueConstraint("client_generated_id", name="uq_user_suggestions_client_generated_id"),
    )
    op.create_index("ix_user_suggestions_kind", "user_suggestions", ["kind"])
    op.create_index("ix_user_suggestions_place_id", "user_suggestions", ["place_id"])
    op.create_index("ix_user_suggestions_subject_type", "user_suggestions", ["subject_type"])
    op.create_index("ix_user_suggestions_subject_id", "user_suggestions", ["subject_id"])
    op.create_index("ix_user_suggestions_status", "user_suggestions", ["status"])

    op.create_table(
        "moderation_items",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("ref_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(32), nullable=True),
        sa.Column("assigned_to", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reason", sa.String(1000), nullable=True),
        sa.UniqueConstraint("kind", "ref_id", name="uq_moderation_items_kind_ref"),
    )
    op.create_index("ix_moderation_items_kind", "moderation_items", ["kind"])
    op.create_index("ix_moderation_items_ref_id", "moderation_items", ["ref_id"])
    op.create_index("ix_moderation_items_status_kind", "moderation_items", ["status", "kind"])
    op.create_index("ix_moderation_items_priority", "moderation_items", ["priority"])

    op.create_table(
        "abuse_reports",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("target_kind", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(UUID_LEN), nullable=False),
        sa.Column("subject_type", sa.String(SUBJECT_TYPE_LEN), nullable=True),
        sa.Column("subject_id", sa.String(UUID_LEN), nullable=True),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(STATUS_LEN), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_abuse_reports_target_kind", "abuse_reports", ["target_kind"])
    op.create_index("ix_abuse_reports_target_id", "abuse_reports", ["target_id"])
    op.create_index("ix_abuse_reports_subject_type", "abuse_reports", ["subject_type"])
    op.create_index("ix_abuse_reports_subject_id", "abuse_reports", ["subject_id"])
    op.create_index("ix_abuse_reports_reason", "abuse_reports", ["reason"])
    op.create_index("ix_abuse_reports_status", "abuse_reports", ["status"])

    op.create_table(
        "user_foundation_audit_logs",
        sa.Column("id", sa.String(UUID_LEN), primary_key=True),
        sa.Column("actor_type", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(UUID_LEN), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target_kind", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(UUID_LEN), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_foundation_audit_logs_actor_type", "user_foundation_audit_logs", ["actor_type"])
    op.create_index("ix_user_foundation_audit_logs_actor_id", "user_foundation_audit_logs", ["actor_id"])
    op.create_index("ix_user_foundation_audit_logs_action", "user_foundation_audit_logs", ["action"])
    op.create_index("ix_user_foundation_audit_logs_target_kind", "user_foundation_audit_logs", ["target_kind"])
    op.create_index("ix_user_foundation_audit_logs_target_id", "user_foundation_audit_logs", ["target_id"])
    op.create_index("ix_user_foundation_audit_logs_request_id", "user_foundation_audit_logs", ["request_id"])


def downgrade() -> None:
    op.drop_table("user_foundation_audit_logs")
    op.drop_table("abuse_reports")
    op.drop_table("moderation_items")
    op.drop_table("user_suggestions")
    op.drop_table("user_photos")
    op.drop_table("place_rating_aggregates")
    op.drop_table("review_votes")
    op.drop_table("reviews")
    op.drop_table("route_history")
    op.drop_table("saved_routes")
    op.drop_index("uq_favorite_places_active_subject_place", table_name="favorite_places")
    op.drop_table("favorite_places")
    op.drop_table("user_preferences")
    op.drop_table("user_profiles")
    op.drop_table("identity_link_events")
    op.drop_table("telegram_identities")
    op.drop_table("external_identities")
    op.drop_table("anonymous_identities")
    op.drop_table("users")
