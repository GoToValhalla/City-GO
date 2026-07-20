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
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "de447288c917"
down_revision = "9e1a2b3c4d5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('admin_bulk_operations',
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
    op.create_index(op.f('ix_admin_bulk_operations_actor'), 'admin_bulk_operations', ['actor'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_completed_at'), 'admin_bulk_operations', ['completed_at'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_created_at'), 'admin_bulk_operations', ['created_at'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_dry_run_operation_id'), 'admin_bulk_operations', ['dry_run_operation_id'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_id'), 'admin_bulk_operations', ['id'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_mode'), 'admin_bulk_operations', ['mode'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_operation_type'), 'admin_bulk_operations', ['operation_type'], unique=False)
    op.create_index(op.f('ix_admin_bulk_operations_status'), 'admin_bulk_operations', ['status'], unique=False)
    op.create_table('admin_kill_switches',
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
    op.create_index(op.f('ix_admin_kill_switches_action'), 'admin_kill_switches', ['action'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_actor'), 'admin_kill_switches', ['actor'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_created_at'), 'admin_kill_switches', ['created_at'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_expires_at'), 'admin_kill_switches', ['expires_at'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_id'), 'admin_kill_switches', ['id'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_status'), 'admin_kill_switches', ['status'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_switch_scope'), 'admin_kill_switches', ['switch_scope'], unique=False)
    op.create_index(op.f('ix_admin_kill_switches_target'), 'admin_kill_switches', ['target'], unique=False)
    op.create_table('extraction_candidates',
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
    op.create_index(op.f('ix_extraction_candidates_created_at'), 'extraction_candidates', ['created_at'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_id'), 'extraction_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_is_enabled'), 'extraction_candidates', ['is_enabled'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_module_code'), 'extraction_candidates', ['module_code'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_owner'), 'extraction_candidates', ['owner'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_readiness_status'), 'extraction_candidates', ['readiness_status'], unique=False)
    op.create_index(op.f('ix_extraction_candidates_target_service_name'), 'extraction_candidates', ['target_service_name'], unique=False)
    op.create_table('integration_contracts',
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
    op.create_index(op.f('ix_integration_contracts_compatibility_policy'), 'integration_contracts', ['compatibility_policy'], unique=False)
    op.create_index(op.f('ix_integration_contracts_consumer'), 'integration_contracts', ['consumer'], unique=False)
    op.create_index(op.f('ix_integration_contracts_created_at'), 'integration_contracts', ['created_at'], unique=False)
    op.create_index(op.f('ix_integration_contracts_id'), 'integration_contracts', ['id'], unique=False)
    op.create_index(op.f('ix_integration_contracts_producer'), 'integration_contracts', ['producer'], unique=False)
    op.create_index(op.f('ix_integration_contracts_protocol'), 'integration_contracts', ['protocol'], unique=False)
    op.create_index(op.f('ix_integration_contracts_status'), 'integration_contracts', ['status'], unique=False)
    op.create_index(op.f('ix_integration_contracts_version'), 'integration_contracts', ['version'], unique=False)
    op.create_table('module_boundaries',
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
    op.create_index(op.f('ix_module_boundaries_created_at'), 'module_boundaries', ['created_at'], unique=False)
    op.create_index(op.f('ix_module_boundaries_id'), 'module_boundaries', ['id'], unique=False)
    op.create_index(op.f('ix_module_boundaries_module_code'), 'module_boundaries', ['module_code'], unique=False)
    op.create_index(op.f('ix_module_boundaries_owner'), 'module_boundaries', ['owner'], unique=False)
    op.create_index(op.f('ix_module_boundaries_status'), 'module_boundaries', ['status'], unique=False)
    op.create_table('prompt_versions',
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
    op.create_index(op.f('ix_prompt_versions_activated_at'), 'prompt_versions', ['activated_at'], unique=False)
    op.create_index(op.f('ix_prompt_versions_created_at'), 'prompt_versions', ['created_at'], unique=False)
    op.create_index(op.f('ix_prompt_versions_id'), 'prompt_versions', ['id'], unique=False)
    op.create_index(op.f('ix_prompt_versions_output_schema_version'), 'prompt_versions', ['output_schema_version'], unique=False)
    op.create_index(op.f('ix_prompt_versions_owner'), 'prompt_versions', ['owner'], unique=False)
    op.create_index(op.f('ix_prompt_versions_prompt_hash'), 'prompt_versions', ['prompt_hash'], unique=False)
    op.create_index(op.f('ix_prompt_versions_status'), 'prompt_versions', ['status'], unique=False)
    op.create_index(op.f('ix_prompt_versions_task_type'), 'prompt_versions', ['task_type'], unique=False)
    op.create_index(op.f('ix_prompt_versions_version'), 'prompt_versions', ['version'], unique=False)
    op.create_table('publication_transition_rules',
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
    op.create_index(op.f('ix_publication_transition_rules_created_at'), 'publication_transition_rules', ['created_at'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_entity_type'), 'publication_transition_rules', ['entity_type'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_from_state'), 'publication_transition_rules', ['from_state'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_id'), 'publication_transition_rules', ['id'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_is_destructive'), 'publication_transition_rules', ['is_destructive'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_required_quality_gate'), 'publication_transition_rules', ['required_quality_gate'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_required_role'), 'publication_transition_rules', ['required_role'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_status'), 'publication_transition_rules', ['status'], unique=False)
    op.create_index(op.f('ix_publication_transition_rules_to_state'), 'publication_transition_rules', ['to_state'], unique=False)
    op.create_table('quality_gate_rules',
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
    op.create_index(op.f('ix_quality_gate_rules_created_at'), 'quality_gate_rules', ['created_at'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_entity_type'), 'quality_gate_rules', ['entity_type'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_gate_code'), 'quality_gate_rules', ['gate_code'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_id'), 'quality_gate_rules', ['id'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_metric_name'), 'quality_gate_rules', ['metric_name'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_severity'), 'quality_gate_rules', ['severity'], unique=False)
    op.create_index(op.f('ix_quality_gate_rules_status'), 'quality_gate_rules', ['status'], unique=False)
    op.create_table('rollback_requests',
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
    op.create_index(op.f('ix_rollback_requests_created_at'), 'rollback_requests', ['created_at'], unique=False)
    op.create_index(op.f('ix_rollback_requests_executed_at'), 'rollback_requests', ['executed_at'], unique=False)
    op.create_index(op.f('ix_rollback_requests_id'), 'rollback_requests', ['id'], unique=False)
    op.create_index(op.f('ix_rollback_requests_requested_by'), 'rollback_requests', ['requested_by'], unique=False)
    op.create_index(op.f('ix_rollback_requests_source_event_id'), 'rollback_requests', ['source_event_id'], unique=False)
    op.create_index(op.f('ix_rollback_requests_status'), 'rollback_requests', ['status'], unique=False)
    op.create_index(op.f('ix_rollback_requests_target_id'), 'rollback_requests', ['target_id'], unique=False)
    op.create_index(op.f('ix_rollback_requests_target_snapshot_version'), 'rollback_requests', ['target_snapshot_version'], unique=False)
    op.create_index(op.f('ix_rollback_requests_target_type'), 'rollback_requests', ['target_type'], unique=False)
    op.create_table('strangler_adapters',
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
    op.create_index(op.f('ix_strangler_adapters_adapter_mode'), 'strangler_adapters', ['adapter_mode'], unique=False)
    op.create_index(op.f('ix_strangler_adapters_created_at'), 'strangler_adapters', ['created_at'], unique=False)
    op.create_index(op.f('ix_strangler_adapters_id'), 'strangler_adapters', ['id'], unique=False)
    op.create_index(op.f('ix_strangler_adapters_source_module'), 'strangler_adapters', ['source_module'], unique=False)
    op.create_index(op.f('ix_strangler_adapters_status'), 'strangler_adapters', ['status'], unique=False)
    op.create_index(op.f('ix_strangler_adapters_target_service'), 'strangler_adapters', ['target_service'], unique=False)
    op.create_table('cost_budget_policies',
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
    op.create_index(op.f('ix_cost_budget_policies_action_when_exceeded'), 'cost_budget_policies', ['action_when_exceeded'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_city_id'), 'cost_budget_policies', ['city_id'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_created_at'), 'cost_budget_policies', ['created_at'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_id'), 'cost_budget_policies', ['id'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_model_name'), 'cost_budget_policies', ['model_name'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_model_provider'), 'cost_budget_policies', ['model_provider'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_period'), 'cost_budget_policies', ['period'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_status'), 'cost_budget_policies', ['status'], unique=False)
    op.create_index(op.f('ix_cost_budget_policies_task_type'), 'cost_budget_policies', ['task_type'], unique=False)
    op.create_table('destination_launch_pipeline_runs',
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
    op.create_index(op.f('ix_destination_launch_pipeline_runs_city_id'), 'destination_launch_pipeline_runs', ['city_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_created_at'), 'destination_launch_pipeline_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_finished_at'), 'destination_launch_pipeline_runs', ['finished_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_id'), 'destination_launch_pipeline_runs', ['id'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_pipeline_key'), 'destination_launch_pipeline_runs', ['pipeline_key'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_requested_by'), 'destination_launch_pipeline_runs', ['requested_by'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_started_at'), 'destination_launch_pipeline_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_status'), 'destination_launch_pipeline_runs', ['status'], unique=False)
    op.create_index(op.f('ix_destination_launch_pipeline_runs_trigger_source'), 'destination_launch_pipeline_runs', ['trigger_source'], unique=False)
    op.create_table('destination_launch_states',
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
    op.create_index(op.f('ix_destination_launch_states_actor'), 'destination_launch_states', ['actor'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_city_id'), 'destination_launch_states', ['city_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_created_at'), 'destination_launch_states', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_current_step'), 'destination_launch_states', ['current_step'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_destination_key'), 'destination_launch_states', ['destination_key'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_id'), 'destination_launch_states', ['id'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_is_published'), 'destination_launch_states', ['is_published'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_is_route_ready'), 'destination_launch_states', ['is_route_ready'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_launch_status'), 'destination_launch_states', ['launch_status'], unique=False)
    op.create_index(op.f('ix_destination_launch_states_readiness_score'), 'destination_launch_states', ['readiness_score'], unique=False)
    op.create_table('golden_datasets',
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
    op.create_index(op.f('ix_golden_datasets_city_id'), 'golden_datasets', ['city_id'], unique=False)
    op.create_index(op.f('ix_golden_datasets_created_at'), 'golden_datasets', ['created_at'], unique=False)
    op.create_index(op.f('ix_golden_datasets_dataset_version'), 'golden_datasets', ['dataset_version'], unique=False)
    op.create_index(op.f('ix_golden_datasets_id'), 'golden_datasets', ['id'], unique=False)
    op.create_index(op.f('ix_golden_datasets_locale'), 'golden_datasets', ['locale'], unique=False)
    op.create_index(op.f('ix_golden_datasets_status'), 'golden_datasets', ['status'], unique=False)
    op.create_index(op.f('ix_golden_datasets_task_type'), 'golden_datasets', ['task_type'], unique=False)
    op.create_table('projection_rebuild_jobs',
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
    op.create_index(op.f('ix_projection_rebuild_jobs_city_id'), 'projection_rebuild_jobs', ['city_id'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_created_at'), 'projection_rebuild_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_finished_at'), 'projection_rebuild_jobs', ['finished_at'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_id'), 'projection_rebuild_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_projection_type'), 'projection_rebuild_jobs', ['projection_type'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_source_snapshot_version'), 'projection_rebuild_jobs', ['source_snapshot_version'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_started_at'), 'projection_rebuild_jobs', ['started_at'], unique=False)
    op.create_index(op.f('ix_projection_rebuild_jobs_status'), 'projection_rebuild_jobs', ['status'], unique=False)
    op.create_table('route_candidate_sets',
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
    op.create_index(op.f('ix_route_candidate_sets_built_at'), 'route_candidate_sets', ['built_at'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_city_id'), 'route_candidate_sets', ['city_id'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_freshness_status'), 'route_candidate_sets', ['freshness_status'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_id'), 'route_candidate_sets', ['id'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_profile'), 'route_candidate_sets', ['profile'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_route_policy'), 'route_candidate_sets', ['route_policy'], unique=False)
    op.create_index(op.f('ix_route_candidate_sets_source_snapshot_version'), 'route_candidate_sets', ['source_snapshot_version'], unique=False)
    op.create_table('destination_launch_checklist_items',
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
    op.create_index(op.f('ix_destination_launch_checklist_items_city_id'), 'destination_launch_checklist_items', ['city_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_completed_at'), 'destination_launch_checklist_items', ['completed_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_completed_by'), 'destination_launch_checklist_items', ['completed_by'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_created_at'), 'destination_launch_checklist_items', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_id'), 'destination_launch_checklist_items', ['id'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_is_required_for_live'), 'destination_launch_checklist_items', ['is_required_for_live'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_item_code'), 'destination_launch_checklist_items', ['item_code'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_pipeline_run_id'), 'destination_launch_checklist_items', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_checklist_items_status'), 'destination_launch_checklist_items', ['status'], unique=False)
    op.create_table('destination_launch_events',
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
    op.create_index(op.f('ix_destination_launch_events_actor'), 'destination_launch_events', ['actor'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_city_id'), 'destination_launch_events', ['city_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_created_at'), 'destination_launch_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_event_type'), 'destination_launch_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_id'), 'destination_launch_events', ['id'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_next_status'), 'destination_launch_events', ['next_status'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_pipeline_run_id'), 'destination_launch_events', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_events_previous_status'), 'destination_launch_events', ['previous_status'], unique=False)
    op.create_table('destination_launch_steps',
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
    op.create_index(op.f('ix_destination_launch_steps_created_at'), 'destination_launch_steps', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_finished_at'), 'destination_launch_steps', ['finished_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_id'), 'destination_launch_steps', ['id'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_pipeline_run_id'), 'destination_launch_steps', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_started_at'), 'destination_launch_steps', ['started_at'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_status'), 'destination_launch_steps', ['status'], unique=False)
    op.create_index(op.f('ix_destination_launch_steps_step_key'), 'destination_launch_steps', ['step_key'], unique=False)
    op.create_table('destination_readiness_summaries',
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
    op.create_index(op.f('ix_destination_readiness_summaries_city_id'), 'destination_readiness_summaries', ['city_id'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_created_at'), 'destination_readiness_summaries', ['created_at'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_id'), 'destination_readiness_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_is_publishable'), 'destination_readiness_summaries', ['is_publishable'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_is_route_ready'), 'destination_readiness_summaries', ['is_route_ready'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_pipeline_run_id'), 'destination_readiness_summaries', ['pipeline_run_id'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_readiness_score'), 'destination_readiness_summaries', ['readiness_score'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_routing_projection_ready'), 'destination_readiness_summaries', ['routing_projection_ready'], unique=False)
    op.create_index(op.f('ix_destination_readiness_summaries_search_projection_ready'), 'destination_readiness_summaries', ['search_projection_ready'], unique=False)
    op.create_table('evaluation_cases',
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
    op.create_index(op.f('ix_evaluation_cases_case_key'), 'evaluation_cases', ['case_key'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_created_at'), 'evaluation_cases', ['created_at'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_dataset_id'), 'evaluation_cases', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_expected_decision'), 'evaluation_cases', ['expected_decision'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_id'), 'evaluation_cases', ['id'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_is_active'), 'evaluation_cases', ['is_active'], unique=False)
    op.create_index(op.f('ix_evaluation_cases_severity'), 'evaluation_cases', ['severity'], unique=False)
    op.create_table('import_runs',
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
    op.create_index(op.f('ix_import_runs_city_id'), 'import_runs', ['city_id'], unique=False)
    op.create_index(op.f('ix_import_runs_created_at'), 'import_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_import_runs_finished_at'), 'import_runs', ['finished_at'], unique=False)
    op.create_index(op.f('ix_import_runs_id'), 'import_runs', ['id'], unique=False)
    op.create_index(op.f('ix_import_runs_provider'), 'import_runs', ['provider'], unique=False)
    op.create_index(op.f('ix_import_runs_run_key'), 'import_runs', ['run_key'], unique=False)
    op.create_index(op.f('ix_import_runs_run_type'), 'import_runs', ['run_type'], unique=False)
    op.create_index(op.f('ix_import_runs_scope_id'), 'import_runs', ['scope_id'], unique=False)
    op.create_index(op.f('ix_import_runs_started_at'), 'import_runs', ['started_at'], unique=False)
    op.create_index(op.f('ix_import_runs_status'), 'import_runs', ['status'], unique=False)
    op.create_table('regression_gate_runs',
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
    op.create_index(op.f('ix_regression_gate_runs_created_at'), 'regression_gate_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_dataset_id'), 'regression_gate_runs', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_finished_at'), 'regression_gate_runs', ['finished_at'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_id'), 'regression_gate_runs', ['id'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_model_name'), 'regression_gate_runs', ['model_name'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_model_provider'), 'regression_gate_runs', ['model_provider'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_prompt_version_id'), 'regression_gate_runs', ['prompt_version_id'], unique=False)
    op.create_index(op.f('ix_regression_gate_runs_status'), 'regression_gate_runs', ['status'], unique=False)
    op.create_table('ai_task_runs',
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
    op.create_index(op.f('ix_ai_task_runs_city_id'), 'ai_task_runs', ['city_id'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_created_at'), 'ai_task_runs', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_finished_at'), 'ai_task_runs', ['finished_at'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_id'), 'ai_task_runs', ['id'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_input_hash'), 'ai_task_runs', ['input_hash'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_model_name'), 'ai_task_runs', ['model_name'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_model_provider'), 'ai_task_runs', ['model_provider'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_place_id'), 'ai_task_runs', ['place_id'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_prompt_hash'), 'ai_task_runs', ['prompt_hash'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_prompt_version'), 'ai_task_runs', ['prompt_version'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_status'), 'ai_task_runs', ['status'], unique=False)
    op.create_index(op.f('ix_ai_task_runs_task_type'), 'ai_task_runs', ['task_type'], unique=False)
    op.create_table('import_run_batches',
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
    op.create_index(op.f('ix_import_run_batches_batch_key'), 'import_run_batches', ['batch_key'], unique=False)
    op.create_index(op.f('ix_import_run_batches_created_at'), 'import_run_batches', ['created_at'], unique=False)
    op.create_index(op.f('ix_import_run_batches_finished_at'), 'import_run_batches', ['finished_at'], unique=False)
    op.create_index(op.f('ix_import_run_batches_id'), 'import_run_batches', ['id'], unique=False)
    op.create_index(op.f('ix_import_run_batches_import_run_id'), 'import_run_batches', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_import_run_batches_started_at'), 'import_run_batches', ['started_at'], unique=False)
    op.create_index(op.f('ix_import_run_batches_status'), 'import_run_batches', ['status'], unique=False)
    op.create_table('place_change_reviews',
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
    op.create_index(op.f('ix_place_change_reviews_city_id'), 'place_change_reviews', ['city_id'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_created_at'), 'place_change_reviews', ['created_at'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_field_name'), 'place_change_reviews', ['field_name'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_id'), 'place_change_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_place_id'), 'place_change_reviews', ['place_id'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_reason'), 'place_change_reviews', ['reason'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_source'), 'place_change_reviews', ['source'], unique=False)
    op.create_index(op.f('ix_place_change_reviews_status'), 'place_change_reviews', ['status'], unique=False)
    op.create_table('place_fact_versions',
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
    op.create_index(op.f('ix_place_fact_versions_created_at'), 'place_fact_versions', ['created_at'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_created_by'), 'place_fact_versions', ['created_by'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_decided_at'), 'place_fact_versions', ['decided_at'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_field_name'), 'place_fact_versions', ['field_name'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_id'), 'place_fact_versions', ['id'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_locale'), 'place_fact_versions', ['locale'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_place_id'), 'place_fact_versions', ['place_id'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_source_ref'), 'place_fact_versions', ['source_ref'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_source_type'), 'place_fact_versions', ['source_type'], unique=False)
    op.create_index(op.f('ix_place_fact_versions_status'), 'place_fact_versions', ['status'], unique=False)
    op.create_table('place_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=64), nullable=False),
    sa.Column('snapshot_data', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_place_snapshots_created_at'), 'place_snapshots', ['created_at'], unique=False)
    op.create_index(op.f('ix_place_snapshots_id'), 'place_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_place_snapshots_place_id'), 'place_snapshots', ['place_id'], unique=False)
    op.create_index(op.f('ix_place_snapshots_reason'), 'place_snapshots', ['reason'], unique=False)
    op.create_table('publication_events',
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
    op.create_index(op.f('ix_publication_events_actor'), 'publication_events', ['actor'], unique=False)
    op.create_index(op.f('ix_publication_events_city_id'), 'publication_events', ['city_id'], unique=False)
    op.create_index(op.f('ix_publication_events_created_at'), 'publication_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_publication_events_event_type'), 'publication_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_publication_events_id'), 'publication_events', ['id'], unique=False)
    op.create_index(op.f('ix_publication_events_is_replayed'), 'publication_events', ['is_replayed'], unique=False)
    op.create_index(op.f('ix_publication_events_next_state'), 'publication_events', ['next_state'], unique=False)
    op.create_index(op.f('ix_publication_events_place_id'), 'publication_events', ['place_id'], unique=False)
    op.create_index(op.f('ix_publication_events_previous_state'), 'publication_events', ['previous_state'], unique=False)
    op.create_index(op.f('ix_publication_events_snapshot_version'), 'publication_events', ['snapshot_version'], unique=False)
    op.create_table('published_place_snapshots',
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
    op.create_index(op.f('ix_published_place_snapshots_city_id'), 'published_place_snapshots', ['city_id'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_created_at'), 'published_place_snapshots', ['created_at'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_id'), 'published_place_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_is_catalog_visible'), 'published_place_snapshots', ['is_catalog_visible'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_is_public'), 'published_place_snapshots', ['is_public'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_is_route_visible'), 'published_place_snapshots', ['is_route_visible'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_is_search_visible'), 'published_place_snapshots', ['is_search_visible'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_locale'), 'published_place_snapshots', ['locale'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_place_id'), 'published_place_snapshots', ['place_id'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_publication_status'), 'published_place_snapshots', ['publication_status'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_snapshot_version'), 'published_place_snapshots', ['snapshot_version'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_source_event_id'), 'published_place_snapshots', ['source_event_id'], unique=False)
    op.create_index(op.f('ix_published_place_snapshots_source_event_type'), 'published_place_snapshots', ['source_event_type'], unique=False)
    op.create_table('review_decisions',
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
    op.create_index(op.f('ix_review_decisions_actor'), 'review_decisions', ['actor'], unique=False)
    op.create_index(op.f('ix_review_decisions_created_at'), 'review_decisions', ['created_at'], unique=False)
    op.create_index(op.f('ix_review_decisions_decision'), 'review_decisions', ['decision'], unique=False)
    op.create_index(op.f('ix_review_decisions_id'), 'review_decisions', ['id'], unique=False)
    op.create_index(op.f('ix_review_decisions_place_id'), 'review_decisions', ['place_id'], unique=False)
    op.create_index(op.f('ix_review_decisions_target_id'), 'review_decisions', ['target_id'], unique=False)
    op.create_index(op.f('ix_review_decisions_target_type'), 'review_decisions', ['target_type'], unique=False)
    op.create_table('routing_place_nodes',
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
    op.create_index(op.f('ix_routing_place_nodes_built_at'), 'routing_place_nodes', ['built_at'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_category'), 'routing_place_nodes', ['category'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_city_id'), 'routing_place_nodes', ['city_id'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_freshness_status'), 'routing_place_nodes', ['freshness_status'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_id'), 'routing_place_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_is_route_visible'), 'routing_place_nodes', ['is_route_visible'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_place_id'), 'routing_place_nodes', ['place_id'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_quality_score'), 'routing_place_nodes', ['quality_score'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_route_policy'), 'routing_place_nodes', ['route_policy'], unique=False)
    op.create_index(op.f('ix_routing_place_nodes_source_snapshot_version'), 'routing_place_nodes', ['source_snapshot_version'], unique=False)
    op.create_table('search_place_documents',
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
    op.create_index(op.f('ix_search_place_documents_built_at'), 'search_place_documents', ['built_at'], unique=False)
    op.create_index(op.f('ix_search_place_documents_category'), 'search_place_documents', ['category'], unique=False)
    op.create_index(op.f('ix_search_place_documents_city_id'), 'search_place_documents', ['city_id'], unique=False)
    op.create_index(op.f('ix_search_place_documents_freshness_status'), 'search_place_documents', ['freshness_status'], unique=False)
    op.create_index(op.f('ix_search_place_documents_id'), 'search_place_documents', ['id'], unique=False)
    op.create_index(op.f('ix_search_place_documents_is_public'), 'search_place_documents', ['is_public'], unique=False)
    op.create_index(op.f('ix_search_place_documents_is_search_visible'), 'search_place_documents', ['is_search_visible'], unique=False)
    op.create_index(op.f('ix_search_place_documents_locale'), 'search_place_documents', ['locale'], unique=False)
    op.create_index(op.f('ix_search_place_documents_place_id'), 'search_place_documents', ['place_id'], unique=False)
    op.create_index(op.f('ix_search_place_documents_ranking_score'), 'search_place_documents', ['ranking_score'], unique=False)
    op.create_index(op.f('ix_search_place_documents_source_snapshot_version'), 'search_place_documents', ['source_snapshot_version'], unique=False)
    op.create_table('ai_candidates',
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
    op.create_index(op.f('ix_ai_candidates_ai_task_run_id'), 'ai_candidates', ['ai_task_run_id'], unique=False)
    op.create_index(op.f('ix_ai_candidates_created_at'), 'ai_candidates', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_candidates_decided_at'), 'ai_candidates', ['decided_at'], unique=False)
    op.create_index(op.f('ix_ai_candidates_field_name'), 'ai_candidates', ['field_name'], unique=False)
    op.create_index(op.f('ix_ai_candidates_id'), 'ai_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_ai_candidates_locale'), 'ai_candidates', ['locale'], unique=False)
    op.create_index(op.f('ix_ai_candidates_place_fact_version_id'), 'ai_candidates', ['place_fact_version_id'], unique=False)
    op.create_index(op.f('ix_ai_candidates_place_id'), 'ai_candidates', ['place_id'], unique=False)
    op.create_index(op.f('ix_ai_candidates_status'), 'ai_candidates', ['status'], unique=False)
    op.create_table('import_conflict_candidates',
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
    op.create_index(op.f('ix_import_conflict_candidates_conflict_score'), 'import_conflict_candidates', ['conflict_score'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_conflict_type'), 'import_conflict_candidates', ['conflict_type'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_created_at'), 'import_conflict_candidates', ['created_at'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_id'), 'import_conflict_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_import_run_id'), 'import_conflict_candidates', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_matched_place_id'), 'import_conflict_candidates', ['matched_place_id'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_resolution_status'), 'import_conflict_candidates', ['resolution_status'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_resolved_at'), 'import_conflict_candidates', ['resolved_at'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_resolved_by'), 'import_conflict_candidates', ['resolved_by'], unique=False)
    op.create_index(op.f('ix_import_conflict_candidates_source_observation_id'), 'import_conflict_candidates', ['source_observation_id'], unique=False)
    op.create_table('import_dead_letter_items',
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
    op.create_index(op.f('ix_import_dead_letter_items_created_at'), 'import_dead_letter_items', ['created_at'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_error_class'), 'import_dead_letter_items', ['error_class'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_id'), 'import_dead_letter_items', ['id'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_import_batch_id'), 'import_dead_letter_items', ['import_batch_id'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_import_run_id'), 'import_dead_letter_items', ['import_run_id'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_last_replay_at'), 'import_dead_letter_items', ['last_replay_at'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_payload_hash'), 'import_dead_letter_items', ['payload_hash'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_replay_status'), 'import_dead_letter_items', ['replay_status'], unique=False)
    op.create_index(op.f('ix_import_dead_letter_items_source_observation_id'), 'import_dead_letter_items', ['source_observation_id'], unique=False)


def downgrade() -> None:
    op.drop_table('import_dead_letter_items')
    op.drop_table('import_conflict_candidates')
    op.drop_table('ai_candidates')
    op.drop_table('search_place_documents')
    op.drop_table('routing_place_nodes')
    op.drop_table('review_decisions')
    op.drop_table('published_place_snapshots')
    op.drop_table('publication_events')
    op.drop_table('place_snapshots')
    op.drop_table('place_fact_versions')
    op.drop_table('place_change_reviews')
    op.drop_table('import_run_batches')
    op.drop_table('ai_task_runs')
    op.drop_table('regression_gate_runs')
    op.drop_table('import_runs')
    op.drop_table('evaluation_cases')
    op.drop_table('destination_readiness_summaries')
    op.drop_table('destination_launch_steps')
    op.drop_table('destination_launch_events')
    op.drop_table('destination_launch_checklist_items')
    op.drop_table('route_candidate_sets')
    op.drop_table('projection_rebuild_jobs')
    op.drop_table('golden_datasets')
    op.drop_table('destination_launch_states')
    op.drop_table('destination_launch_pipeline_runs')
    op.drop_table('cost_budget_policies')
    op.drop_table('strangler_adapters')
    op.drop_table('rollback_requests')
    op.drop_table('quality_gate_rules')
    op.drop_table('publication_transition_rules')
    op.drop_table('prompt_versions')
    op.drop_table('module_boundaries')
    op.drop_table('integration_contracts')
    op.drop_table('extraction_candidates')
    op.drop_table('admin_kill_switches')
    op.drop_table('admin_bulk_operations')
