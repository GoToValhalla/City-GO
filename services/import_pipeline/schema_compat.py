"""Import-critical schema compatibility checks and repair."""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateTable

from db.base import Base
from models.data_foundation import PlaceFieldProvenance
from models.place import Place

IMPORT_PLACE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("place_layer", "VARCHAR(64) NOT NULL DEFAULT 'tourist_catalog'"),
    ("route_policy", "VARCHAR(64) NOT NULL DEFAULT 'city_walking'"),
    ("tourist_eligible", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("transport_required", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("primary_destination_id", "INTEGER"),
    ("destination_assignment_stale", "BOOLEAN NOT NULL DEFAULT FALSE"),
)
# Writer-used columns (source_observation_service.py, place_enrichment_sources.py,
# import_pipeline_foundation_steps.py, data/scripts/import_city_osm.py) that were
# added to the SourceObservation model but never shipped in a migration.
IMPORT_SOURCE_OBSERVATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("source_license", "VARCHAR(255)"),
    ("attribution_text", "VARCHAR(1000)"),
    ("idempotency_key", "VARCHAR(255)"),
)
IMPORT_CRITICAL_TABLES: tuple[str, ...] = (PlaceFieldProvenance.__tablename__,)


def is_schema_mismatch_error(error: BaseException | str | None) -> bool:
    text_value = str(error or "").lower()
    markers = (
        "undefinedcolumn",
        "undefinedtable",
        "does not exist",
        "no such column",
        "no such table",
        "unknown column",
    )
    return any(marker in text_value for marker in markers)


def collecting_has_schema_failure(summary: dict[str, object] | None) -> bool:
    if not isinstance(summary, dict):
        return False
    if is_schema_mismatch_error(str(summary.get("last_error") or "")):
        return True
    scope_errors = summary.get("scope_errors")
    if not isinstance(scope_errors, list):
        return False
    return any(
        isinstance(row, dict) and is_schema_mismatch_error(str(row.get("error") or ""))
        for row in scope_errors
    )


def diagnose_import_schema_gaps(engine: Engine) -> dict[str, list[str]]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    missing_tables = [name for name in IMPORT_CRITICAL_TABLES if name not in table_names]
    place_columns = {column["name"] for column in inspector.get_columns("places")} if "places" in table_names else set()
    missing_columns = [name for name, _sql in IMPORT_PLACE_COLUMNS if name not in place_columns]
    source_observation_columns = (
        {column["name"] for column in inspector.get_columns("source_observations")}
        if "source_observations" in table_names
        else set()
    )
    missing_source_observation_columns = [
        name for name, _sql in IMPORT_SOURCE_OBSERVATION_COLUMNS if name not in source_observation_columns
    ]
    return {
        "missing_tables": missing_tables,
        "missing_place_columns": missing_columns,
        "missing_source_observation_columns": missing_source_observation_columns,
    }


def ensure_import_pipeline_schema(engine: Engine) -> dict[str, Any]:
    gaps = diagnose_import_schema_gaps(engine)
    created_tables: list[str] = []
    added_columns: list[str] = []
    connection = engine.connect()
    try:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())
        for table_name in IMPORT_CRITICAL_TABLES:
            if table_name in existing_tables:
                continue
            table = Base.metadata.tables[table_name]
            connection.execute(CreateTable(table))
            connection.commit()
            created_tables.append(table_name)
            existing_tables.add(table_name)
        if "places" in existing_tables:
            place_columns = {column["name"] for column in inspector.get_columns("places")}
            for column_name, ddl in IMPORT_PLACE_COLUMNS:
                if column_name in place_columns:
                    continue
                connection.execute(text(f"ALTER TABLE places ADD COLUMN {column_name} {ddl}"))
                connection.commit()
                added_columns.append(f"places.{column_name}")
        if "source_observations" in existing_tables:
            source_observation_columns = {column["name"] for column in inspector.get_columns("source_observations")}
            for column_name, ddl in IMPORT_SOURCE_OBSERVATION_COLUMNS:
                if column_name in source_observation_columns:
                    continue
                connection.execute(text(f"ALTER TABLE source_observations ADD COLUMN {column_name} {ddl}"))
                connection.commit()
                added_columns.append(f"source_observations.{column_name}")
            existing_indexes = {index["name"] for index in inspector.get_indexes("source_observations")}
            if "ix_source_observations_source_license" not in existing_indexes:
                connection.execute(
                    text("CREATE INDEX ix_source_observations_source_license ON source_observations (source_license)")
                )
                connection.commit()
            if "ix_source_observations_idempotency_key" not in existing_indexes:
                connection.execute(
                    text("CREATE INDEX ix_source_observations_idempotency_key ON source_observations (idempotency_key)")
                )
                connection.commit()
            existing_unique_constraints = {
                constraint["name"] for constraint in inspector.get_unique_constraints("source_observations")
            }
            if (
                "uq_source_observation_idempotency_key" not in existing_unique_constraints
                and "uq_source_observation_idempotency_key" not in existing_indexes
            ):
                # unique index instead of ADD CONSTRAINT ... UNIQUE: equivalent enforcement, works on SQLite too.
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_source_observation_idempotency_key "
                        "ON source_observations (idempotency_key)"
                    )
                )
                connection.commit()
    finally:
        connection.close()
    return {"created_tables": created_tables, "added_columns": added_columns, "before": gaps}
