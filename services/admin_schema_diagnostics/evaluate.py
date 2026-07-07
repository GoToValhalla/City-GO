"""Evaluate schema contracts against a read-only snapshot."""

from __future__ import annotations

from services.admin_schema_diagnostics.contracts import SCHEMA_CONTRACTS, SchemaContract


def evaluate_contract(
    contract: SchemaContract,
    *,
    existing_tables: set[str],
    existing_columns: dict[str, set[str]],
) -> dict[str, object]:
    missing_tables = [name for name in contract.tables if name not in existing_tables]
    missing_columns: list[str] = []
    existing_contract_tables = [name for name in contract.tables if name in existing_tables]
    existing_contract_columns: list[str] = []
    for table, required in contract.columns.items():
        if table not in existing_tables:
            continue
        present = existing_columns.get(table, set())
        for column in required:
            label = f"{table}.{column}"
            if column in present:
                existing_contract_columns.append(label)
            else:
                missing_columns.append(label)
    status = "ok" if not missing_tables and not missing_columns else "schema_drift"
    return {
        "status": status,
        "missing_tables": missing_tables,
        "missing_columns": sorted(missing_columns),
        "existing_tables": existing_contract_tables,
        "existing_columns": sorted(existing_contract_columns),
        "extra_info": {"tables_in_contract": list(contract.tables), "columns_checked": len(existing_contract_columns) + len(missing_columns)},
    }


def evaluate_all_contracts(
    *,
    existing_tables: set[str],
    existing_columns: dict[str, set[str]],
) -> dict[str, dict[str, object]]:
    return {
        contract.key: evaluate_contract(contract, existing_tables=existing_tables, existing_columns=existing_columns)
        for contract in SCHEMA_CONTRACTS
    }
