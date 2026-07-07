"""Build admin DB schema diagnostics payload."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.engine import Engine

from services.admin_schema_diagnostics.collect import read_alembic_version, read_schema_snapshot
from services.admin_schema_diagnostics.evaluate import evaluate_all_contracts


def build_db_schema_diagnostics(engine: Engine) -> dict[str, object]:
    checked_at = datetime.now(timezone.utc).isoformat()
    alembic_version = read_alembic_version(engine)
    existing_tables, existing_columns = read_schema_snapshot(engine)
    contracts = evaluate_all_contracts(existing_tables=existing_tables, existing_columns=existing_columns)
    missing_total = sum(
        len(item.get("missing_tables", [])) + len(item.get("missing_columns", []))
        for item in contracts.values()
        if isinstance(item, dict)
    )
    columns_checked = sum(
        int((item.get("extra_info") or {}).get("columns_checked", 0))
        for item in contracts.values()
        if isinstance(item, dict)
    )
    tables_checked = len(existing_tables)
    status = "ok" if missing_total == 0 else "schema_drift"
    return {
        "status": status,
        "alembic_version": alembic_version,
        "checked_at": checked_at,
        "contracts": contracts,
        "raw_summary": {
            "tables_checked": tables_checked,
            "columns_checked": columns_checked,
            "missing_total": missing_total,
        },
    }
