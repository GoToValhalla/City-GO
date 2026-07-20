"""add missing tables for models registered without a migration

Revision ID: de447288c917
Revises: 9e1a2b3c4d5f
Create Date: 2026-07-20

Root cause: models/data_foundation_stage1.py, import_discipline_stage2.py,
intelligence_discipline_stage3.py, publication_admin_stage4.py,
search_routing_stage5.py, service_extraction_stage6.py,
destination_launch_pipeline.py, place_snapshot.py,
place_published_snapshot.py, and place_change_review.py were added to
models/__init__.py (and, where wired, into routers/services) without a
corresponding Alembic migration. `alembic check` against a real PostgreSQL
16 database confirmed these tables never existed outside test create_all().
This migration creates only those tables/indexes; it intentionally excludes
unrelated pre-existing drift (index renames, JSON->JSONB type changes on
user_signals, telegram_identities, user_preferences, user_foundation_audit_logs,
user_suggestions, workflow_operations, admin_operations, and others) surfaced
by the same alembic check run, which predates this change and is out of scope.

Production incompatibility fix: the first version of this migration used
unconditional `op.create_table(...)` for all 36 tables and failed in
production with "relation \"place_change_reviews\" already exists" —
production's alembic_version was still 6b9c1e4a8d3f (this migration had
never run), yet place_change_reviews already existed, created outside this
Alembic chain (models/place_change_review.py documents it as a legacy table
kept only for historical schema/data compatibility; it predates every
migration in this chain). The same could be true, in principle, of any of
the other 35 tables on a sufficiently old/hand-patched production database
(see scripts/prod_schema_guard.py, which exists precisely because production
schema has drifted ahead of Alembic before via non-Alembic paths).

Every table this migration creates is now routed through
services.migration_column_guard.ensure_table, the same idempotent,
ownership-tracked pattern already used for column-level drift by
84665d0fd500/f0c0c48aa12a (see that module's docstring for the original
incident this pattern fixes). For each table: if it does not exist, create
it and tag it with a `COMMENT ON TABLE ... IS 'created_by_revision:...'` so
downgrade() can later tell it apart from a pre-existing production table. If
it already exists, verify every column the model declares is present and
type/nullability-compatible; raise IncompatibleTableError *before any
mutation* if not — this fails closed rather than silently adopting a
partial/incompatible schema. Indexes go through the equivalent
services.migration_column_guard.ensure_index (skip-if-exists, tag-if-created)
so a table adopted from production does not fail on a duplicate index either.
downgrade() only drops tables/indexes this revision actually created;
pre-existing production tables such as place_change_reviews are left alone.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from services import migration_column_guard

revision = "de447288c917"
down_revision = "9e1a2b3c4d5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()
    # Reflect FK-target tables that predate this migration so
    # ForeignKeyConstraint(['x'], ['cities.id']) et al. can resolve their
    # remote column against a real sa.Table on the SAME metadata — SQLAlchemy's
    # DDL compiler requires this even when the target table already physically
    # exists in the database; a fresh per-table MetaData() cannot see it.
    for external_table in ('cities', 'places', 'city_import_scopes', 'source_observations'):
        sa.Table(external_table, metadata, autoload_with=connection)

    # admin_bulk_operations
    table = sa.Table('admin_bulk_operations', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('operation_type', sa.String(length=64), nullable=False),
    sa.Column('target_filter', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('mode', sa.String(length=32), nullable=False),
    sa.Column('dry_run_operation_id', sa.Integer(), nullable=True),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.String(length=1000), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('affected_count', sa.Integer(), nullable=False),
    sa.Column('skipped_count', sa.Integer(), nullable=False),
    sa.Column('failed_count', sa.Integer(), nullable=False),
    sa.Column('result_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_actor', table='admin_bulk_operations', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_completed_at', table='admin_bulk_operations', columns=['completed_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_created_at', table='admin_bulk_operations', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_dry_run_operation_id', table='admin_bulk_operations', columns=['dry_run_operation_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_id', table='admin_bulk_operations', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_mode', table='admin_bulk_operations', columns=['mode'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_operation_type', table='admin_bulk_operations', columns=['operation_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_bulk_operations_status', table='admin_bulk_operations', columns=['status'], unique=False
    )

    # admin_kill_switches
    table = sa.Table('admin_kill_switches', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('switch_scope', sa.String(length=64), nullable=False),
    sa.Column('target', sa.String(length=255), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_action', table='admin_kill_switches', columns=['action'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_actor', table='admin_kill_switches', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_created_at', table='admin_kill_switches', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_expires_at', table='admin_kill_switches', columns=['expires_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_id', table='admin_kill_switches', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_status', table='admin_kill_switches', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_switch_scope', table='admin_kill_switches', columns=['switch_scope'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_admin_kill_switches_target', table='admin_kill_switches', columns=['target'], unique=False
    )

    # extraction_candidates
    table = sa.Table('extraction_candidates', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_code', sa.String(length=100), nullable=False),
    sa.Column('target_service_name', sa.String(length=255), nullable=False),
    sa.Column('owner', sa.String(length=255), nullable=False),
    sa.Column('readiness_status', sa.String(length=32), nullable=False),
    sa.Column('api_contract_ref', sa.String(length=1000), nullable=True),
    sa.Column('event_contract_ref', sa.String(length=1000), nullable=True),
    sa.Column('data_migration_plan_ref', sa.String(length=1000), nullable=True),
    sa.Column('rollback_plan_ref', sa.String(length=1000), nullable=True),
    sa.Column('is_enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('module_code', 'target_service_name', name='uq_extraction_candidate_module_service')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_created_at', table='extraction_candidates', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_id', table='extraction_candidates', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_is_enabled', table='extraction_candidates', columns=['is_enabled'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_module_code', table='extraction_candidates', columns=['module_code'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_owner', table='extraction_candidates', columns=['owner'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_readiness_status', table='extraction_candidates', columns=['readiness_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_extraction_candidates_target_service_name', table='extraction_candidates', columns=['target_service_name'], unique=False
    )

    # integration_contracts
    table = sa.Table('integration_contracts', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('producer', sa.String(length=100), nullable=False),
    sa.Column('consumer', sa.String(length=100), nullable=False),
    sa.Column('protocol', sa.String(length=64), nullable=False),
    sa.Column('schema_ref', sa.String(length=1000), nullable=False),
    sa.Column('version', sa.String(length=64), nullable=False),
    sa.Column('compatibility_policy', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('producer', 'consumer', 'version', name='uq_integration_contract_version')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_compatibility_policy', table='integration_contracts', columns=['compatibility_policy'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_consumer', table='integration_contracts', columns=['consumer'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_created_at', table='integration_contracts', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_id', table='integration_contracts', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_producer', table='integration_contracts', columns=['producer'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_protocol', table='integration_contracts', columns=['protocol'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_status', table='integration_contracts', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_integration_contracts_version', table='integration_contracts', columns=['version'], unique=False
    )

    # module_boundaries
    table = sa.Table('module_boundaries', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_code', sa.String(length=100), nullable=False),
    sa.Column('owner', sa.String(length=255), nullable=False),
    sa.Column('source_of_truth_tables', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('allowed_dependencies', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('emitted_events', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('consumed_events', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('module_code', name='uq_module_boundary_code')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_module_boundaries_created_at', table='module_boundaries', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_module_boundaries_id', table='module_boundaries', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_module_boundaries_module_code', table='module_boundaries', columns=['module_code'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_module_boundaries_owner', table='module_boundaries', columns=['owner'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_module_boundaries_status', table='module_boundaries', columns=['status'], unique=False
    )

    # prompt_versions
    table = sa.Table('prompt_versions', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_type', sa.String(length=64), nullable=False),
    sa.Column('version', sa.String(length=64), nullable=False),
    sa.Column('prompt_hash', sa.String(length=128), nullable=False),
    sa.Column('prompt_reference', sa.String(length=1000), nullable=True),
    sa.Column('output_schema_version', sa.String(length=64), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('rollout_policy', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('owner', sa.String(length=255), nullable=True),
    sa.Column('changelog', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('activated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('prompt_hash', name='uq_prompt_version_hash'),
    sa.UniqueConstraint('task_type', 'version', name='uq_prompt_version_task_version')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_activated_at', table='prompt_versions', columns=['activated_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_created_at', table='prompt_versions', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_id', table='prompt_versions', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_output_schema_version', table='prompt_versions', columns=['output_schema_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_owner', table='prompt_versions', columns=['owner'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_prompt_hash', table='prompt_versions', columns=['prompt_hash'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_status', table='prompt_versions', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_task_type', table='prompt_versions', columns=['task_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_prompt_versions_version', table='prompt_versions', columns=['version'], unique=False
    )

    # publication_transition_rules
    table = sa.Table('publication_transition_rules', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=False),
    sa.Column('from_state', sa.String(length=32), nullable=False),
    sa.Column('to_state', sa.String(length=32), nullable=False),
    sa.Column('required_role', sa.String(length=64), nullable=True),
    sa.Column('required_quality_gate', sa.String(length=100), nullable=True),
    sa.Column('is_destructive', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entity_type', 'from_state', 'to_state', name='uq_publication_transition_rule')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_created_at', table='publication_transition_rules', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_entity_type', table='publication_transition_rules', columns=['entity_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_from_state', table='publication_transition_rules', columns=['from_state'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_id', table='publication_transition_rules', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_is_destructive', table='publication_transition_rules', columns=['is_destructive'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_required_quality_gate', table='publication_transition_rules', columns=['required_quality_gate'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_required_role', table='publication_transition_rules', columns=['required_role'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_status', table='publication_transition_rules', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_transition_rules_to_state', table='publication_transition_rules', columns=['to_state'], unique=False
    )

    # quality_gate_rules
    table = sa.Table('quality_gate_rules', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('gate_code', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=64), nullable=False),
    sa.Column('metric_name', sa.String(length=100), nullable=False),
    sa.Column('operator', sa.String(length=16), nullable=False),
    sa.Column('threshold_value', sa.Float(), nullable=True),
    sa.Column('severity', sa.String(length=32), nullable=False),
    sa.Column('failure_message', sa.String(length=1000), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('gate_code', name='uq_quality_gate_rule_code')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_created_at', table='quality_gate_rules', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_entity_type', table='quality_gate_rules', columns=['entity_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_gate_code', table='quality_gate_rules', columns=['gate_code'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_id', table='quality_gate_rules', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_metric_name', table='quality_gate_rules', columns=['metric_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_severity', table='quality_gate_rules', columns=['severity'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_quality_gate_rules_status', table='quality_gate_rules', columns=['status'], unique=False
    )

    # rollback_requests
    table = sa.Table('rollback_requests', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('target_type', sa.String(length=64), nullable=False),
    sa.Column('target_id', sa.Integer(), nullable=False),
    sa.Column('target_snapshot_version', sa.Integer(), nullable=False),
    sa.Column('source_event_id', sa.Integer(), nullable=True),
    sa.Column('requested_by', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.String(length=1000), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('executed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_created_at', table='rollback_requests', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_executed_at', table='rollback_requests', columns=['executed_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_id', table='rollback_requests', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_requested_by', table='rollback_requests', columns=['requested_by'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_source_event_id', table='rollback_requests', columns=['source_event_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_status', table='rollback_requests', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_target_id', table='rollback_requests', columns=['target_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_target_snapshot_version', table='rollback_requests', columns=['target_snapshot_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_rollback_requests_target_type', table='rollback_requests', columns=['target_type'], unique=False
    )

    # strangler_adapters
    table = sa.Table('strangler_adapters', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_module', sa.String(length=100), nullable=False),
    sa.Column('target_service', sa.String(length=255), nullable=False),
    sa.Column('adapter_mode', sa.String(length=64), nullable=False),
    sa.Column('read_strategy', sa.String(length=255), nullable=False),
    sa.Column('write_strategy', sa.String(length=255), nullable=False),
    sa.Column('fallback_strategy', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_adapter_mode', table='strangler_adapters', columns=['adapter_mode'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_created_at', table='strangler_adapters', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_id', table='strangler_adapters', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_source_module', table='strangler_adapters', columns=['source_module'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_status', table='strangler_adapters', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_strangler_adapters_target_service', table='strangler_adapters', columns=['target_service'], unique=False
    )

    # cost_budget_policies
    table = sa.Table('cost_budget_policies', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_type', sa.String(length=64), nullable=False),
    sa.Column('model_provider', sa.String(length=64), nullable=True),
    sa.Column('model_name', sa.String(length=128), nullable=True),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('period', sa.String(length=32), nullable=False),
    sa.Column('max_tokens', sa.Integer(), nullable=True),
    sa.Column('max_cost_amount', sa.Float(), nullable=True),
    sa.Column('action_when_exceeded', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_action_when_exceeded', table='cost_budget_policies', columns=['action_when_exceeded'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_city_id', table='cost_budget_policies', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_created_at', table='cost_budget_policies', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_id', table='cost_budget_policies', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_model_name', table='cost_budget_policies', columns=['model_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_model_provider', table='cost_budget_policies', columns=['model_provider'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_period', table='cost_budget_policies', columns=['period'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_status', table='cost_budget_policies', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_cost_budget_policies_task_type', table='cost_budget_policies', columns=['task_type'], unique=False
    )

    # destination_launch_pipeline_runs
    table = sa.Table('destination_launch_pipeline_runs', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('pipeline_key', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=64), nullable=False),
    sa.Column('requested_by', sa.String(length=255), nullable=False),
    sa.Column('trigger_source', sa.String(length=64), nullable=False),
    sa.Column('processed_steps_count', sa.Integer(), nullable=False),
    sa.Column('failed_steps_count', sa.Integer(), nullable=False),
    sa.Column('skipped_steps_count', sa.Integer(), nullable=False),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('run_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pipeline_key', name='uq_destination_launch_pipeline_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_city_id', table='destination_launch_pipeline_runs', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_created_at', table='destination_launch_pipeline_runs', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_finished_at', table='destination_launch_pipeline_runs', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_id', table='destination_launch_pipeline_runs', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_pipeline_key', table='destination_launch_pipeline_runs', columns=['pipeline_key'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_requested_by', table='destination_launch_pipeline_runs', columns=['requested_by'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_started_at', table='destination_launch_pipeline_runs', columns=['started_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_status', table='destination_launch_pipeline_runs', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_pipeline_runs_trigger_source', table='destination_launch_pipeline_runs', columns=['trigger_source'], unique=False
    )

    # destination_launch_states
    table = sa.Table('destination_launch_states', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('destination_key', sa.String(length=255), nullable=False),
    sa.Column('launch_status', sa.String(length=64), nullable=False),
    sa.Column('current_step', sa.String(length=100), nullable=True),
    sa.Column('actor', sa.String(length=255), nullable=True),
    sa.Column('reason', sa.String(length=1000), nullable=True),
    sa.Column('readiness_score', sa.Float(), nullable=False),
    sa.Column('blocking_reason', sa.Text(), nullable=True),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('is_route_ready', sa.Boolean(), nullable=False),
    sa.Column('state_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('city_id', name='uq_destination_launch_state_city'),
    sa.UniqueConstraint('destination_key', name='uq_destination_launch_state_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_actor', table='destination_launch_states', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_city_id', table='destination_launch_states', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_created_at', table='destination_launch_states', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_current_step', table='destination_launch_states', columns=['current_step'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_destination_key', table='destination_launch_states', columns=['destination_key'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_id', table='destination_launch_states', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_is_published', table='destination_launch_states', columns=['is_published'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_is_route_ready', table='destination_launch_states', columns=['is_route_ready'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_launch_status', table='destination_launch_states', columns=['launch_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_states_readiness_score', table='destination_launch_states', columns=['readiness_score'], unique=False
    )

    # golden_datasets
    table = sa.Table('golden_datasets', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_type', sa.String(length=64), nullable=False),
    sa.Column('dataset_version', sa.String(length=64), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('minimum_pass_rate', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('task_type', 'dataset_version', name='uq_golden_dataset_task_version')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_city_id', table='golden_datasets', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_created_at', table='golden_datasets', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_dataset_version', table='golden_datasets', columns=['dataset_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_id', table='golden_datasets', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_locale', table='golden_datasets', columns=['locale'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_status', table='golden_datasets', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_golden_datasets_task_type', table='golden_datasets', columns=['task_type'], unique=False
    )

    # projection_rebuild_jobs
    table = sa.Table('projection_rebuild_jobs', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('projection_type', sa.String(length=64), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('source_snapshot_version', sa.Integer(), nullable=True),
    sa.Column('processed_count', sa.Integer(), nullable=False),
    sa.Column('rebuilt_count', sa.Integer(), nullable=False),
    sa.Column('skipped_count', sa.Integer(), nullable=False),
    sa.Column('failed_count', sa.Integer(), nullable=False),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_city_id', table='projection_rebuild_jobs', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_created_at', table='projection_rebuild_jobs', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_finished_at', table='projection_rebuild_jobs', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_id', table='projection_rebuild_jobs', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_projection_type', table='projection_rebuild_jobs', columns=['projection_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_source_snapshot_version', table='projection_rebuild_jobs', columns=['source_snapshot_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_started_at', table='projection_rebuild_jobs', columns=['started_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_projection_rebuild_jobs_status', table='projection_rebuild_jobs', columns=['status'], unique=False
    )

    # route_candidate_sets
    table = sa.Table('route_candidate_sets', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('profile', sa.String(length=64), nullable=False),
    sa.Column('route_policy', sa.String(length=64), nullable=False),
    sa.Column('source_snapshot_version', sa.Integer(), nullable=False),
    sa.Column('candidate_count', sa.Integer(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('freshness_status', sa.String(length=32), nullable=False),
    sa.Column('built_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('city_id', 'profile', 'route_policy', 'source_snapshot_version', name='uq_route_candidate_set_scope')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_built_at', table='route_candidate_sets', columns=['built_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_city_id', table='route_candidate_sets', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_freshness_status', table='route_candidate_sets', columns=['freshness_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_id', table='route_candidate_sets', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_profile', table='route_candidate_sets', columns=['profile'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_route_policy', table='route_candidate_sets', columns=['route_policy'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_route_candidate_sets_source_snapshot_version', table='route_candidate_sets', columns=['source_snapshot_version'], unique=False
    )

    # destination_launch_checklist_items
    table = sa.Table('destination_launch_checklist_items', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('pipeline_run_id', sa.Integer(), nullable=True),
    sa.Column('item_code', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=64), nullable=False),
    sa.Column('is_required_for_live', sa.Boolean(), nullable=False),
    sa.Column('evidence_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('blocking_reason', sa.Text(), nullable=True),
    sa.Column('completed_by', sa.String(length=255), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['destination_launch_pipeline_runs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('city_id', 'item_code', name='uq_destination_launch_checklist_city_item')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_city_id', table='destination_launch_checklist_items', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_completed_at', table='destination_launch_checklist_items', columns=['completed_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_completed_by', table='destination_launch_checklist_items', columns=['completed_by'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_created_at', table='destination_launch_checklist_items', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_id', table='destination_launch_checklist_items', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_is_required_for_live', table='destination_launch_checklist_items', columns=['is_required_for_live'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_item_code', table='destination_launch_checklist_items', columns=['item_code'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_pipeline_run_id', table='destination_launch_checklist_items', columns=['pipeline_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_checklist_items_status', table='destination_launch_checklist_items', columns=['status'], unique=False
    )

    # destination_launch_events
    table = sa.Table('destination_launch_events', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('pipeline_run_id', sa.Integer(), nullable=True),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('previous_status', sa.String(length=64), nullable=True),
    sa.Column('next_status', sa.String(length=64), nullable=True),
    sa.Column('actor', sa.String(length=255), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('event_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['destination_launch_pipeline_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_actor', table='destination_launch_events', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_city_id', table='destination_launch_events', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_created_at', table='destination_launch_events', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_event_type', table='destination_launch_events', columns=['event_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_id', table='destination_launch_events', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_next_status', table='destination_launch_events', columns=['next_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_pipeline_run_id', table='destination_launch_events', columns=['pipeline_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_events_previous_status', table='destination_launch_events', columns=['previous_status'], unique=False
    )

    # destination_launch_steps
    table = sa.Table('destination_launch_steps', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('pipeline_run_id', sa.Integer(), nullable=False),
    sa.Column('step_key', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=64), nullable=False),
    sa.Column('input_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('output_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['destination_launch_pipeline_runs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('pipeline_run_id', 'step_key', name='uq_destination_launch_step_run_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_created_at', table='destination_launch_steps', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_finished_at', table='destination_launch_steps', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_id', table='destination_launch_steps', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_pipeline_run_id', table='destination_launch_steps', columns=['pipeline_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_started_at', table='destination_launch_steps', columns=['started_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_status', table='destination_launch_steps', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_launch_steps_step_key', table='destination_launch_steps', columns=['step_key'], unique=False
    )

    # destination_readiness_summaries
    table = sa.Table('destination_readiness_summaries', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('pipeline_run_id', sa.Integer(), nullable=True),
    sa.Column('readiness_score', sa.Float(), nullable=False),
    sa.Column('places_total', sa.Integer(), nullable=False),
    sa.Column('places_publishable', sa.Integer(), nullable=False),
    sa.Column('places_route_eligible', sa.Integer(), nullable=False),
    sa.Column('photo_coverage_pct', sa.Float(), nullable=False),
    sa.Column('address_coverage_pct', sa.Float(), nullable=False),
    sa.Column('hours_coverage_pct', sa.Float(), nullable=False),
    sa.Column('description_coverage_pct', sa.Float(), nullable=False),
    sa.Column('duplicate_candidates_count', sa.Integer(), nullable=False),
    sa.Column('conflict_candidates_count', sa.Integer(), nullable=False),
    sa.Column('blocking_issues', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('is_publishable', sa.Boolean(), nullable=False),
    sa.Column('is_route_ready', sa.Boolean(), nullable=False),
    sa.Column('search_projection_ready', sa.Boolean(), nullable=False),
    sa.Column('routing_projection_ready', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['pipeline_run_id'], ['destination_launch_pipeline_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_city_id', table='destination_readiness_summaries', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_created_at', table='destination_readiness_summaries', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_id', table='destination_readiness_summaries', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_is_publishable', table='destination_readiness_summaries', columns=['is_publishable'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_is_route_ready', table='destination_readiness_summaries', columns=['is_route_ready'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_pipeline_run_id', table='destination_readiness_summaries', columns=['pipeline_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_readiness_score', table='destination_readiness_summaries', columns=['readiness_score'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_routing_projection_ready', table='destination_readiness_summaries', columns=['routing_projection_ready'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_destination_readiness_summaries_search_projection_ready', table='destination_readiness_summaries', columns=['search_projection_ready'], unique=False
    )

    # evaluation_cases
    table = sa.Table('evaluation_cases', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dataset_id', sa.Integer(), nullable=False),
    sa.Column('case_key', sa.String(length=255), nullable=False),
    sa.Column('input_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('expected_output', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('expected_decision', sa.String(length=64), nullable=True),
    sa.Column('severity', sa.String(length=32), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['golden_datasets.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dataset_id', 'case_key', name='uq_evaluation_case_dataset_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_case_key', table='evaluation_cases', columns=['case_key'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_created_at', table='evaluation_cases', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_dataset_id', table='evaluation_cases', columns=['dataset_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_expected_decision', table='evaluation_cases', columns=['expected_decision'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_id', table='evaluation_cases', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_is_active', table='evaluation_cases', columns=['is_active'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_evaluation_cases_severity', table='evaluation_cases', columns=['severity'], unique=False
    )

    # import_runs
    table = sa.Table('import_runs', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_key', sa.String(length=255), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('scope_id', sa.Integer(), nullable=True),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('run_type', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('checkpoint_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('quality_summary', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('processed_count', sa.Integer(), nullable=False),
    sa.Column('created_count', sa.Integer(), nullable=False),
    sa.Column('matched_count', sa.Integer(), nullable=False),
    sa.Column('rejected_count', sa.Integer(), nullable=False),
    sa.Column('failed_count', sa.Integer(), nullable=False),
    sa.Column('error_summary', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['scope_id'], ['city_import_scopes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('run_key', name='uq_import_run_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_city_id', table='import_runs', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_created_at', table='import_runs', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_finished_at', table='import_runs', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_id', table='import_runs', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_provider', table='import_runs', columns=['provider'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_run_key', table='import_runs', columns=['run_key'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_run_type', table='import_runs', columns=['run_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_scope_id', table='import_runs', columns=['scope_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_started_at', table='import_runs', columns=['started_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_runs_status', table='import_runs', columns=['status'], unique=False
    )

    # regression_gate_runs
    table = sa.Table('regression_gate_runs', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('prompt_version_id', sa.Integer(), nullable=False),
    sa.Column('dataset_id', sa.Integer(), nullable=False),
    sa.Column('model_provider', sa.String(length=64), nullable=False),
    sa.Column('model_name', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('pass_rate', sa.Float(), nullable=False),
    sa.Column('failed_cases_count', sa.Integer(), nullable=False),
    sa.Column('total_cases_count', sa.Integer(), nullable=False),
    sa.Column('score_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('failure_summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['dataset_id'], ['golden_datasets.id'], ),
    sa.ForeignKeyConstraint(['prompt_version_id'], ['prompt_versions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_created_at', table='regression_gate_runs', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_dataset_id', table='regression_gate_runs', columns=['dataset_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_finished_at', table='regression_gate_runs', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_id', table='regression_gate_runs', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_model_name', table='regression_gate_runs', columns=['model_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_model_provider', table='regression_gate_runs', columns=['model_provider'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_prompt_version_id', table='regression_gate_runs', columns=['prompt_version_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_regression_gate_runs_status', table='regression_gate_runs', columns=['status'], unique=False
    )

    # ai_task_runs
    table = sa.Table('ai_task_runs', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('place_id', sa.Integer(), nullable=True),
    sa.Column('task_type', sa.String(length=64), nullable=False),
    sa.Column('model_provider', sa.String(length=64), nullable=False),
    sa.Column('model_name', sa.String(length=128), nullable=False),
    sa.Column('prompt_version', sa.String(length=64), nullable=True),
    sa.Column('prompt_hash', sa.String(length=128), nullable=True),
    sa.Column('input_hash', sa.String(length=128), nullable=False),
    sa.Column('input_reference', sa.String(length=500), nullable=True),
    sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('tokens_in', sa.Integer(), nullable=False),
    sa.Column('tokens_out', sa.Integer(), nullable=False),
    sa.Column('cost_amount', sa.Float(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_city_id', table='ai_task_runs', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_created_at', table='ai_task_runs', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_finished_at', table='ai_task_runs', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_id', table='ai_task_runs', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_input_hash', table='ai_task_runs', columns=['input_hash'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_model_name', table='ai_task_runs', columns=['model_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_model_provider', table='ai_task_runs', columns=['model_provider'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_place_id', table='ai_task_runs', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_prompt_hash', table='ai_task_runs', columns=['prompt_hash'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_prompt_version', table='ai_task_runs', columns=['prompt_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_status', table='ai_task_runs', columns=['status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_task_runs_task_type', table='ai_task_runs', columns=['task_type'], unique=False
    )

    # import_run_batches
    table = sa.Table('import_run_batches', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('import_run_id', sa.Integer(), nullable=False),
    sa.Column('batch_key', sa.String(length=255), nullable=False),
    sa.Column('provider_cursor', sa.String(length=1000), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('checkpoint_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('processed_count', sa.Integer(), nullable=False),
    sa.Column('created_count', sa.Integer(), nullable=False),
    sa.Column('matched_count', sa.Integer(), nullable=False),
    sa.Column('rejected_count', sa.Integer(), nullable=False),
    sa.Column('failed_count', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['import_run_id'], ['import_runs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('import_run_id', 'batch_key', name='uq_import_run_batch_key')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_batch_key', table='import_run_batches', columns=['batch_key'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_created_at', table='import_run_batches', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_finished_at', table='import_run_batches', columns=['finished_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_id', table='import_run_batches', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_import_run_id', table='import_run_batches', columns=['import_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_started_at', table='import_run_batches', columns=['started_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_run_batches_status', table='import_run_batches', columns=['status'], unique=False
    )

    # place_change_reviews
    table = sa.Table('place_change_reviews', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('field_name', sa.String(length=100), nullable=False),
    sa.Column('old_value', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('new_value', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('reason', sa.String(length=128), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('trust_score', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('resolution', sa.String(length=64), nullable=True),
    sa.Column('review_comment', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_city_id', table='place_change_reviews', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_created_at', table='place_change_reviews', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_field_name', table='place_change_reviews', columns=['field_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_id', table='place_change_reviews', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_place_id', table='place_change_reviews', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_reason', table='place_change_reviews', columns=['reason'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_source', table='place_change_reviews', columns=['source'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_change_reviews_status', table='place_change_reviews', columns=['status'], unique=False
    )

    # place_fact_versions
    table = sa.Table('place_fact_versions', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('field_name', sa.String(length=100), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('source_type', sa.String(length=32), nullable=False),
    sa.Column('source_ref', sa.String(length=255), nullable=True),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('superseded_by_id', sa.Integer(), nullable=True),
    sa.Column('decision_reason', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('decided_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['superseded_by_id'], ['place_fact_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('place_id', 'field_name', 'locale', 'version', name='uq_place_fact_version_place_field_locale_version')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_created_at', table='place_fact_versions', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_created_by', table='place_fact_versions', columns=['created_by'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_decided_at', table='place_fact_versions', columns=['decided_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_field_name', table='place_fact_versions', columns=['field_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_id', table='place_fact_versions', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_locale', table='place_fact_versions', columns=['locale'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_place_id', table='place_fact_versions', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_source_ref', table='place_fact_versions', columns=['source_ref'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_source_type', table='place_fact_versions', columns=['source_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_fact_versions_status', table='place_fact_versions', columns=['status'], unique=False
    )

    # place_snapshots
    table = sa.Table('place_snapshots', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=64), nullable=False),
    sa.Column('snapshot_data', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_snapshots_created_at', table='place_snapshots', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_snapshots_id', table='place_snapshots', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_snapshots_place_id', table='place_snapshots', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_place_snapshots_reason', table='place_snapshots', columns=['reason'], unique=False
    )

    # publication_events
    table = sa.Table('publication_events', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=True),
    sa.Column('city_id', sa.Integer(), nullable=True),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('previous_state', sa.String(length=32), nullable=True),
    sa.Column('next_state', sa.String(length=32), nullable=False),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('reason', sa.String(length=1000), nullable=True),
    sa.Column('snapshot_version', sa.Integer(), nullable=True),
    sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('is_replayed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_actor', table='publication_events', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_city_id', table='publication_events', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_created_at', table='publication_events', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_event_type', table='publication_events', columns=['event_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_id', table='publication_events', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_is_replayed', table='publication_events', columns=['is_replayed'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_next_state', table='publication_events', columns=['next_state'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_place_id', table='publication_events', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_previous_state', table='publication_events', columns=['previous_state'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_publication_events_snapshot_version', table='publication_events', columns=['snapshot_version'], unique=False
    )

    # published_place_snapshots
    table = sa.Table('published_place_snapshots', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('snapshot_version', sa.Integer(), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('publication_status', sa.String(length=32), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('is_catalog_visible', sa.Boolean(), nullable=False),
    sa.Column('is_search_visible', sa.Boolean(), nullable=False),
    sa.Column('is_route_visible', sa.Boolean(), nullable=False),
    sa.Column('snapshot_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('quality_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('media_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('source_event_type', sa.String(length=64), nullable=True),
    sa.Column('source_event_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('place_id', 'snapshot_version', name='uq_published_place_snapshot_place_version')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_city_id', table='published_place_snapshots', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_created_at', table='published_place_snapshots', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_id', table='published_place_snapshots', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_is_catalog_visible', table='published_place_snapshots', columns=['is_catalog_visible'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_is_public', table='published_place_snapshots', columns=['is_public'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_is_route_visible', table='published_place_snapshots', columns=['is_route_visible'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_is_search_visible', table='published_place_snapshots', columns=['is_search_visible'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_locale', table='published_place_snapshots', columns=['locale'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_place_id', table='published_place_snapshots', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_publication_status', table='published_place_snapshots', columns=['publication_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_snapshot_version', table='published_place_snapshots', columns=['snapshot_version'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_source_event_id', table='published_place_snapshots', columns=['source_event_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_published_place_snapshots_source_event_type', table='published_place_snapshots', columns=['source_event_type'], unique=False
    )

    # review_decisions
    table = sa.Table('review_decisions', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('target_type', sa.String(length=64), nullable=False),
    sa.Column('target_id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=True),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.String(length=1000), nullable=True),
    sa.Column('actor', sa.String(length=255), nullable=False),
    sa.Column('previous_value_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('new_value_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_actor', table='review_decisions', columns=['actor'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_created_at', table='review_decisions', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_decision', table='review_decisions', columns=['decision'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_id', table='review_decisions', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_place_id', table='review_decisions', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_target_id', table='review_decisions', columns=['target_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_review_decisions_target_type', table='review_decisions', columns=['target_type'], unique=False
    )

    # routing_place_nodes
    table = sa.Table('routing_place_nodes', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('source_snapshot_version', sa.Integer(), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lng', sa.Float(), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('route_policy', sa.String(length=64), nullable=False),
    sa.Column('average_visit_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('is_route_visible', sa.Boolean(), nullable=False),
    sa.Column('quality_score', sa.Integer(), nullable=False),
    sa.Column('freshness_status', sa.String(length=32), nullable=False),
    sa.Column('built_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('place_id', 'route_policy', 'source_snapshot_version', name='uq_routing_place_node_snapshot')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_built_at', table='routing_place_nodes', columns=['built_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_category', table='routing_place_nodes', columns=['category'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_city_id', table='routing_place_nodes', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_freshness_status', table='routing_place_nodes', columns=['freshness_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_id', table='routing_place_nodes', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_is_route_visible', table='routing_place_nodes', columns=['is_route_visible'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_place_id', table='routing_place_nodes', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_quality_score', table='routing_place_nodes', columns=['quality_score'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_route_policy', table='routing_place_nodes', columns=['route_policy'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_routing_place_nodes_source_snapshot_version', table='routing_place_nodes', columns=['source_snapshot_version'], unique=False
    )

    # search_place_documents
    table = sa.Table('search_place_documents', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('source_snapshot_version', sa.Integer(), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('searchable_text', sa.Text(), nullable=True),
    sa.Column('category', sa.String(length=100), nullable=True),
    sa.Column('tags_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('is_search_visible', sa.Boolean(), nullable=False),
    sa.Column('ranking_score', sa.Float(), nullable=False),
    sa.Column('freshness_status', sa.String(length=32), nullable=False),
    sa.Column('built_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('place_id', 'locale', 'source_snapshot_version', name='uq_search_place_document_snapshot')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_built_at', table='search_place_documents', columns=['built_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_category', table='search_place_documents', columns=['category'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_city_id', table='search_place_documents', columns=['city_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_freshness_status', table='search_place_documents', columns=['freshness_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_id', table='search_place_documents', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_is_public', table='search_place_documents', columns=['is_public'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_is_search_visible', table='search_place_documents', columns=['is_search_visible'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_locale', table='search_place_documents', columns=['locale'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_place_id', table='search_place_documents', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_ranking_score', table='search_place_documents', columns=['ranking_score'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_search_place_documents_source_snapshot_version', table='search_place_documents', columns=['source_snapshot_version'], unique=False
    )

    # ai_candidates
    table = sa.Table('ai_candidates', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ai_task_run_id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('field_name', sa.String(length=100), nullable=False),
    sa.Column('locale', sa.String(length=16), nullable=False),
    sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('validation_result_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('place_fact_version_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('decided_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['ai_task_run_id'], ['ai_task_runs.id'], ),
    sa.ForeignKeyConstraint(['place_fact_version_id'], ['place_fact_versions.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_ai_task_run_id', table='ai_candidates', columns=['ai_task_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_created_at', table='ai_candidates', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_decided_at', table='ai_candidates', columns=['decided_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_field_name', table='ai_candidates', columns=['field_name'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_id', table='ai_candidates', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_locale', table='ai_candidates', columns=['locale'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_place_fact_version_id', table='ai_candidates', columns=['place_fact_version_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_place_id', table='ai_candidates', columns=['place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_ai_candidates_status', table='ai_candidates', columns=['status'], unique=False
    )

    # import_conflict_candidates
    table = sa.Table('import_conflict_candidates', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('import_run_id', sa.Integer(), nullable=True),
    sa.Column('source_observation_id', sa.Integer(), nullable=False),
    sa.Column('matched_place_id', sa.Integer(), nullable=True),
    sa.Column('conflict_type', sa.String(length=64), nullable=False),
    sa.Column('conflict_score', sa.Float(), nullable=True),
    sa.Column('evidence_payload', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('resolution_status', sa.String(length=32), nullable=False),
    sa.Column('resolved_by', sa.String(length=255), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('resolution_reason', sa.String(length=1000), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['import_run_id'], ['import_runs.id'], ),
    sa.ForeignKeyConstraint(['matched_place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['source_observation_id'], ['source_observations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_conflict_score', table='import_conflict_candidates', columns=['conflict_score'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_conflict_type', table='import_conflict_candidates', columns=['conflict_type'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_created_at', table='import_conflict_candidates', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_id', table='import_conflict_candidates', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_import_run_id', table='import_conflict_candidates', columns=['import_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_matched_place_id', table='import_conflict_candidates', columns=['matched_place_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_resolution_status', table='import_conflict_candidates', columns=['resolution_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_resolved_at', table='import_conflict_candidates', columns=['resolved_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_resolved_by', table='import_conflict_candidates', columns=['resolved_by'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_conflict_candidates_source_observation_id', table='import_conflict_candidates', columns=['source_observation_id'], unique=False
    )

    # import_dead_letter_items
    table = sa.Table('import_dead_letter_items', metadata,
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('import_run_id', sa.Integer(), nullable=True),
    sa.Column('import_batch_id', sa.Integer(), nullable=True),
    sa.Column('source_observation_id', sa.Integer(), nullable=True),
    sa.Column('payload_hash', sa.String(length=128), nullable=True),
    sa.Column('payload_reference', sa.String(length=1000), nullable=True),
    sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=True),
    sa.Column('error_class', sa.String(length=255), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('replay_status', sa.String(length=32), nullable=False),
    sa.Column('replay_attempts', sa.Integer(), nullable=False),
    sa.Column('last_replay_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['import_batch_id'], ['import_run_batches.id'], ),
    sa.ForeignKeyConstraint(['import_run_id'], ['import_runs.id'], ),
    sa.ForeignKeyConstraint(['source_observation_id'], ['source_observations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    migration_column_guard.ensure_table(connection, revision=revision, table=table)
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_created_at', table='import_dead_letter_items', columns=['created_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_error_class', table='import_dead_letter_items', columns=['error_class'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_id', table='import_dead_letter_items', columns=['id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_import_batch_id', table='import_dead_letter_items', columns=['import_batch_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_import_run_id', table='import_dead_letter_items', columns=['import_run_id'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_last_replay_at', table='import_dead_letter_items', columns=['last_replay_at'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_payload_hash', table='import_dead_letter_items', columns=['payload_hash'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_replay_status', table='import_dead_letter_items', columns=['replay_status'], unique=False
    )
    migration_column_guard.ensure_index(
        connection, revision=revision, index_name='ix_import_dead_letter_items_source_observation_id', table='import_dead_letter_items', columns=['source_observation_id'], unique=False
    )


def downgrade() -> None:
    connection = op.get_bind()

    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='import_dead_letter_items')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='import_conflict_candidates')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='ai_candidates')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='search_place_documents')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='routing_place_nodes')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='review_decisions')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='published_place_snapshots')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='publication_events')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='place_snapshots')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='place_fact_versions')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='place_change_reviews')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='import_run_batches')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='ai_task_runs')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='regression_gate_runs')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='import_runs')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='evaluation_cases')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_readiness_summaries')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_launch_steps')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_launch_events')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_launch_checklist_items')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='route_candidate_sets')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='projection_rebuild_jobs')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='golden_datasets')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_launch_states')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='destination_launch_pipeline_runs')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='cost_budget_policies')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='strangler_adapters')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='rollback_requests')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='quality_gate_rules')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='publication_transition_rules')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='prompt_versions')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='module_boundaries')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='integration_contracts')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='extraction_candidates')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='admin_kill_switches')
    migration_column_guard.drop_table_if_owned(connection, revision=revision, table_name='admin_bulk_operations')
