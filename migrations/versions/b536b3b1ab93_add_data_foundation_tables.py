"""add data foundation tables

models/data_foundation.py defines PlaceFieldProvenance, CityQualitySnapshot,
CityEnrichmentRun, EnrichmentTask, PlaceStateTransition, CanonicalCategory,
OsmCategoryMapping, SpamPoiRule and QualityScoreHistory, but no migration
ever created their tables. Applying migrations to a fresh database fails
at e6a1b2c3d4f5 ("place card data refresh v1"), whose review_items table
has a foreign key to enrichment_tasks — a table that never existed.

Revision ID: b536b3b1ab93
Revises: d0e1f2a3b4c5
Create Date: 2026-07-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b536b3b1ab93"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB()


def upgrade() -> None:
    json_type = _json_type()

    op.create_table(
        "place_field_provenance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("freshness_status", sa.String(length=32), nullable=False, server_default="fresh"),
        sa.Column("obtained_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_manually_overridden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_value", json_type, nullable=True),
        sa.Column("normalized_value", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "field_name", "source", name="uq_place_field_source"),
    )
    op.create_index(op.f("ix_place_field_provenance_id"), "place_field_provenance", ["id"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_place_id"), "place_field_provenance", ["place_id"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_field_name"), "place_field_provenance", ["field_name"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_source"), "place_field_provenance", ["source"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_freshness_status"), "place_field_provenance", ["freshness_status"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_obtained_at"), "place_field_provenance", ["obtained_at"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_expires_at"), "place_field_provenance", ["expires_at"], unique=False)
    op.create_index(op.f("ix_place_field_provenance_is_manually_overridden"), "place_field_provenance", ["is_manually_overridden"], unique=False)

    op.create_table(
        "city_quality_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="not_ready"),
        sa.Column("total_places_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_places_active", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_places_route_eligible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spam_poi_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spam_poi_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("photo_coverage_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("any_photo_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("address_full_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("address_any_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("description_any_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("hours_any_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gold_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("silver_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bronze_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("draft_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rejected_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_data_age_days", sa.Float(), nullable=True),
        sa.Column("stale_places_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("never_verified_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("snapshot_payload", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_city_quality_snapshots_id"), "city_quality_snapshots", ["id"], unique=False)
    op.create_index(op.f("ix_city_quality_snapshots_city_id"), "city_quality_snapshots", ["city_id"], unique=False)
    op.create_index(op.f("ix_city_quality_snapshots_readiness_score"), "city_quality_snapshots", ["readiness_score"], unique=False)
    op.create_index(op.f("ix_city_quality_snapshots_quality_status"), "city_quality_snapshots", ["quality_status"], unique=False)
    op.create_index(op.f("ix_city_quality_snapshots_created_at"), "city_quality_snapshots", ["created_at"], unique=False)

    op.create_table(
        "city_enrichment_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("requested_city_name", sa.String(length=255), nullable=True),
        sa.Column("run_type", sa.String(length=64), nullable=False, server_default="city_enrichment"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_city_enrichment_runs_id"), "city_enrichment_runs", ["id"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_city_id"), "city_enrichment_runs", ["city_id"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_requested_city_name"), "city_enrichment_runs", ["requested_city_name"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_run_type"), "city_enrichment_runs", ["run_type"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_status"), "city_enrichment_runs", ["status"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_stage"), "city_enrichment_runs", ["stage"], unique=False)
    op.create_index(op.f("ix_city_enrichment_runs_created_at"), "city_enrichment_runs", ["created_at"], unique=False)

    op.create_table(
        "enrichment_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["city_enrichment_runs.id"]),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enrichment_tasks_id"), "enrichment_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_run_id"), "enrichment_tasks", ["run_id"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_city_id"), "enrichment_tasks", ["city_id"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_place_id"), "enrichment_tasks", ["place_id"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_task_type"), "enrichment_tasks", ["task_type"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_status"), "enrichment_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_priority"), "enrichment_tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_next_retry_at"), "enrichment_tasks", ["next_retry_at"], unique=False)
    op.create_index(op.f("ix_enrichment_tasks_created_at"), "enrichment_tasks", ["created_at"], unique=False)

    op.create_table(
        "place_state_transitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), nullable=False, server_default="system"),
        sa.Column("trigger_reason", sa.String(length=1000), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_place_state_transitions_id"), "place_state_transitions", ["id"], unique=False)
    op.create_index(op.f("ix_place_state_transitions_place_id"), "place_state_transitions", ["place_id"], unique=False)
    op.create_index(op.f("ix_place_state_transitions_from_state"), "place_state_transitions", ["from_state"], unique=False)
    op.create_index(op.f("ix_place_state_transitions_to_state"), "place_state_transitions", ["to_state"], unique=False)
    op.create_index(op.f("ix_place_state_transitions_triggered_by"), "place_state_transitions", ["triggered_by"], unique=False)
    op.create_index(op.f("ix_place_state_transitions_triggered_at"), "place_state_transitions", ["triggered_at"], unique=False)

    op.create_table(
        "canonical_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name_ru", sa.String(length=255), nullable=False),
        sa.Column("is_route_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_catalog_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_spam_category", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_canonical_categories_id"), "canonical_categories", ["id"], unique=False)
    op.create_index(op.f("ix_canonical_categories_code"), "canonical_categories", ["code"], unique=True)
    op.create_index(op.f("ix_canonical_categories_is_route_eligible"), "canonical_categories", ["is_route_eligible"], unique=False)
    op.create_index(op.f("ix_canonical_categories_is_catalog_visible"), "canonical_categories", ["is_catalog_visible"], unique=False)
    op.create_index(op.f("ix_canonical_categories_is_default_enabled"), "canonical_categories", ["is_default_enabled"], unique=False)
    op.create_index(op.f("ix_canonical_categories_is_spam_category"), "canonical_categories", ["is_spam_category"], unique=False)

    op.create_table(
        "osm_category_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("osm_key", sa.String(length=100), nullable=False),
        sa.Column("osm_value", sa.String(length=255), nullable=False),
        sa.Column("canonical_category", sa.String(length=100), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_route_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("osm_key", "osm_value", name="uq_osm_category_mapping_tag"),
    )
    op.create_index(op.f("ix_osm_category_mappings_id"), "osm_category_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_osm_category_mappings_osm_key"), "osm_category_mappings", ["osm_key"], unique=False)
    op.create_index(op.f("ix_osm_category_mappings_osm_value"), "osm_category_mappings", ["osm_value"], unique=False)
    op.create_index(op.f("ix_osm_category_mappings_canonical_category"), "osm_category_mappings", ["canonical_category"], unique=False)
    op.create_index(op.f("ix_osm_category_mappings_is_allowed"), "osm_category_mappings", ["is_allowed"], unique=False)
    op.create_index(op.f("ix_osm_category_mappings_is_route_eligible"), "osm_category_mappings", ["is_route_eligible"], unique=False)

    op.create_table(
        "spam_poi_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="osm"),
        sa.Column("osm_key", sa.String(length=100), nullable=False),
        sa.Column("osm_value", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="block"),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "osm_key", "osm_value", name="uq_spam_poi_rule"),
    )
    op.create_index(op.f("ix_spam_poi_rules_id"), "spam_poi_rules", ["id"], unique=False)
    op.create_index(op.f("ix_spam_poi_rules_source"), "spam_poi_rules", ["source"], unique=False)
    op.create_index(op.f("ix_spam_poi_rules_osm_key"), "spam_poi_rules", ["osm_key"], unique=False)
    op.create_index(op.f("ix_spam_poi_rules_osm_value"), "spam_poi_rules", ["osm_value"], unique=False)
    op.create_index(op.f("ix_spam_poi_rules_is_active"), "spam_poi_rules", ["is_active"], unique=False)

    op.create_table(
        "quality_score_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("quality_tier", sa.String(length=32), nullable=False),
        sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photo_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freshness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_score_history_id"), "quality_score_history", ["id"], unique=False)
    op.create_index(op.f("ix_quality_score_history_place_id"), "quality_score_history", ["place_id"], unique=False)
    op.create_index(op.f("ix_quality_score_history_quality_tier"), "quality_score_history", ["quality_tier"], unique=False)
    op.create_index(op.f("ix_quality_score_history_created_at"), "quality_score_history", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("quality_score_history")
    op.drop_table("spam_poi_rules")
    op.drop_table("osm_category_mappings")
    op.drop_table("canonical_categories")
    op.drop_table("place_state_transitions")
    op.drop_table("enrichment_tasks")
    op.drop_table("city_enrichment_runs")
    op.drop_table("city_quality_snapshots")
    op.drop_table("place_field_provenance")
