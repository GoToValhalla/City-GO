"""Idempotent Data Foundation P0 schema/apply script.

Зачем отдельный скрипт:
- в репозитории уже есть Alembic, но без надежного списка head revision в текущем контексте;
- P0 должен быть безопасно применим поверх существующей production БД;
- все ALTER TABLE выполняются через IF NOT EXISTS / guarded DO-блоки.

Запуск:
    python data/scripts/apply_data_foundation_p0.py

Скрипт не заменяет Alembic. После стабилизации нужно перенести DDL в нормальную Alembic migration.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text

from core.config import settings
from models.place import Place
from services.data_foundation_policy import CANONICAL_CATEGORY_SEED, OSM_SPAM_RULE_SEED


def _db_url() -> str:
    # Alembic/SQLAlchemy app uses psycopg driver, оставляем тот же URL.
    return settings.database_url


def _execute_statements(connection, statements: list[str]) -> None:
    for statement in statements:
        connection.execute(text(statement))


def _backfill_canonical_category(connection) -> None:
    """Backfill canonical_category from legacy category via the ORM table (not raw SQL)."""
    table = Place.__table__
    connection.execute(
        table.update()
        .where(table.c.canonical_category.is_(None), table.c.category.isnot(None))
        .values(canonical_category=table.c.category)
    )


def apply_schema() -> None:
    engine = create_engine(_db_url())
    with engine.begin() as connection:
        _execute_statements(
            connection,
            [
                # City metadata.
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS primary_language VARCHAR(16) NOT NULL DEFAULT 'ru'",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS secondary_languages JSONB",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS osm_relation_id VARCHAR(64)",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS boundary JSONB",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS readiness_score INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS quality_status VARCHAR(32) NOT NULL DEFAULT 'not_ready'",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS last_import_at TIMESTAMP",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS next_import_at TIMESTAMP",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS population_tier VARCHAR(32)",
                "ALTER TABLE cities ADD COLUMN IF NOT EXISTS expected_places_count INTEGER",
                # Category flags.
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_route_eligible BOOLEAN NOT NULL DEFAULT TRUE",
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_catalog_visible BOOLEAN NOT NULL DEFAULT TRUE",
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_default_enabled BOOLEAN NOT NULL DEFAULT TRUE",
                "ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_spam_category BOOLEAN NOT NULL DEFAULT FALSE",
                # Place Data Foundation fields.
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS canonical_category VARCHAR(100)",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'active'",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS quality_tier VARCHAR(32) NOT NULL DEFAULT 'silver'",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS quality_score INTEGER NOT NULL DEFAULT 65",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS completeness_score INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS photo_score INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS description_score INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS confidence_score INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS freshness_score INTEGER NOT NULL DEFAULT 3",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS is_spam_poi BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS is_duplicate_suspected BOOLEAN NOT NULL DEFAULT FALSE",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS geo_precision VARCHAR(32)",
                "ALTER TABLE places ADD COLUMN IF NOT EXISTS critical_field_expired BOOLEAN NOT NULL DEFAULT FALSE",
                # Data Foundation tables.
                """
                CREATE TABLE IF NOT EXISTS place_field_provenance (
                    id SERIAL PRIMARY KEY,
                    place_id INTEGER NOT NULL REFERENCES places(id),
                    field_name VARCHAR(100) NOT NULL,
                    source VARCHAR(100) NOT NULL,
                    source_url VARCHAR(1000),
                    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    freshness_status VARCHAR(32) NOT NULL DEFAULT 'fresh',
                    obtained_at TIMESTAMP NOT NULL DEFAULT now(),
                    expires_at TIMESTAMP,
                    is_manually_overridden BOOLEAN NOT NULL DEFAULT FALSE,
                    raw_value JSONB,
                    normalized_value JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS city_quality_snapshots (
                    id SERIAL PRIMARY KEY,
                    city_id INTEGER NOT NULL REFERENCES cities(id),
                    readiness_score INTEGER NOT NULL DEFAULT 0,
                    quality_status VARCHAR(32) NOT NULL DEFAULT 'not_ready',
                    total_places_imported INTEGER NOT NULL DEFAULT 0,
                    total_places_active INTEGER NOT NULL DEFAULT 0,
                    total_places_route_eligible INTEGER NOT NULL DEFAULT 0,
                    spam_poi_count INTEGER NOT NULL DEFAULT 0,
                    spam_poi_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    photo_coverage_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    any_photo_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    address_full_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    address_any_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    description_any_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    hours_any_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    gold_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    silver_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    bronze_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    draft_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    rejected_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    avg_data_age_days DOUBLE PRECISION,
                    stale_places_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    never_verified_pct DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                    snapshot_payload JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS city_enrichment_runs (
                    id SERIAL PRIMARY KEY,
                    city_id INTEGER REFERENCES cities(id),
                    requested_city_name VARCHAR(255),
                    run_type VARCHAR(64) NOT NULL DEFAULT 'city_enrichment',
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    stage VARCHAR(64),
                    progress_total INTEGER NOT NULL DEFAULT 0,
                    progress_done INTEGER NOT NULL DEFAULT 0,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    error_message TEXT,
                    summary JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS enrichment_tasks (
                    id SERIAL PRIMARY KEY,
                    run_id INTEGER REFERENCES city_enrichment_runs(id),
                    city_id INTEGER REFERENCES cities(id),
                    place_id INTEGER REFERENCES places(id),
                    task_type VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'queued',
                    priority INTEGER NOT NULL DEFAULT 100,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    next_retry_at TIMESTAMP,
                    locked_at TIMESTAMP,
                    locked_by VARCHAR(255),
                    last_error TEXT,
                    payload JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS place_state_transitions (
                    id SERIAL PRIMARY KEY,
                    place_id INTEGER NOT NULL REFERENCES places(id),
                    from_state VARCHAR(32),
                    to_state VARCHAR(32) NOT NULL,
                    triggered_by VARCHAR(255) NOT NULL DEFAULT 'system',
                    trigger_reason VARCHAR(1000),
                    metadata JSONB,
                    triggered_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS canonical_categories (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(100) NOT NULL UNIQUE,
                    name_ru VARCHAR(255) NOT NULL,
                    is_route_eligible BOOLEAN NOT NULL DEFAULT TRUE,
                    is_catalog_visible BOOLEAN NOT NULL DEFAULT TRUE,
                    is_default_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    is_spam_category BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS osm_category_mappings (
                    id SERIAL PRIMARY KEY,
                    osm_key VARCHAR(100) NOT NULL,
                    osm_value VARCHAR(255) NOT NULL,
                    canonical_category VARCHAR(100) NOT NULL,
                    is_allowed BOOLEAN NOT NULL DEFAULT TRUE,
                    is_route_eligible BOOLEAN NOT NULL DEFAULT TRUE,
                    comment VARCHAR(1000),
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now(),
                    CONSTRAINT uq_osm_category_mapping_tag UNIQUE (osm_key, osm_value)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS spam_poi_rules (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(64) NOT NULL DEFAULT 'osm',
                    osm_key VARCHAR(100) NOT NULL,
                    osm_value VARCHAR(255) NOT NULL,
                    action VARCHAR(32) NOT NULL DEFAULT 'block',
                    reason VARCHAR(1000),
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP NOT NULL DEFAULT now(),
                    CONSTRAINT uq_spam_poi_rule UNIQUE (source, osm_key, osm_value)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS quality_score_history (
                    id SERIAL PRIMARY KEY,
                    place_id INTEGER NOT NULL REFERENCES places(id),
                    quality_score INTEGER NOT NULL,
                    quality_tier VARCHAR(32) NOT NULL,
                    completeness_score INTEGER NOT NULL DEFAULT 0,
                    photo_score INTEGER NOT NULL DEFAULT 0,
                    description_score INTEGER NOT NULL DEFAULT 0,
                    confidence_score INTEGER NOT NULL DEFAULT 0,
                    freshness_score INTEGER NOT NULL DEFAULT 0,
                    reason VARCHAR(1000),
                    created_at TIMESTAMP NOT NULL DEFAULT now()
                )
                """,
                # Indexes.
                "CREATE INDEX IF NOT EXISTS ix_places_city_slug ON places(city_id, slug)",
                "CREATE INDEX IF NOT EXISTS ix_places_canonical_category ON places(canonical_category)",
                "CREATE INDEX IF NOT EXISTS ix_places_lifecycle_status ON places(lifecycle_status)",
                "CREATE INDEX IF NOT EXISTS ix_places_quality_tier ON places(quality_tier)",
                "CREATE INDEX IF NOT EXISTS ix_places_is_spam_poi ON places(is_spam_poi)",
                "CREATE INDEX IF NOT EXISTS ix_place_field_provenance_place_id ON place_field_provenance(place_id)",
                "CREATE INDEX IF NOT EXISTS ix_city_quality_snapshots_city_id ON city_quality_snapshots(city_id)",
                "CREATE INDEX IF NOT EXISTS ix_enrichment_tasks_status_priority ON enrichment_tasks(status, priority)",
                # Drop global slug unique constraint if it exists, then add city-scoped unique constraint.
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'places_slug_key'
                    ) THEN
                        ALTER TABLE places DROP CONSTRAINT places_slug_key;
                    END IF;
                END $$
                """,
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uq_places_city_id_slug'
                    ) THEN
                        ALTER TABLE places ADD CONSTRAINT uq_places_city_id_slug UNIQUE (city_id, slug);
                    END IF;
                END $$
                """,
            ],
        )
        _backfill_canonical_category(connection)

        for item in CANONICAL_CATEGORY_SEED:
            connection.execute(
                text(
                    """
                    INSERT INTO canonical_categories (
                        code, name_ru, is_route_eligible, is_catalog_visible, is_default_enabled, is_spam_category
                    )
                    VALUES (:code, :name_ru, :is_route_eligible, :is_catalog_visible, :is_default_enabled, :is_spam_category)
                    ON CONFLICT (code) DO UPDATE SET
                        name_ru = EXCLUDED.name_ru,
                        is_route_eligible = EXCLUDED.is_route_eligible,
                        is_catalog_visible = EXCLUDED.is_catalog_visible,
                        is_default_enabled = EXCLUDED.is_default_enabled,
                        is_spam_category = EXCLUDED.is_spam_category,
                        updated_at = now()
                    """
                ),
                item,
            )

        for item in OSM_SPAM_RULE_SEED:
            connection.execute(
                text(
                    """
                    INSERT INTO spam_poi_rules (source, osm_key, osm_value, action, reason, is_active)
                    VALUES ('osm', :osm_key, :osm_value, 'block', :reason, true)
                    ON CONFLICT (source, osm_key, osm_value) DO UPDATE SET
                        action = 'block',
                        reason = EXCLUDED.reason,
                        is_active = true,
                        updated_at = now()
                    """
                ),
                item,
            )


if __name__ == "__main__":
    apply_schema()
    print("Data Foundation P0 schema applied")
