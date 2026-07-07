from __future__ import annotations

from fastapi.testclient import TestClient

from services.admin_schema_diagnostics.contracts import IMPORT_CRITICAL, PHOTO_CRITICAL, ROUTE_CRITICAL
from services.admin_schema_diagnostics.evaluate import evaluate_contract


def test_db_schema_diagnostics_ok_when_contract_present_new(client: TestClient) -> None:
    response = client.get("/admin/diagnostics/db-schema")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["contracts"]["import_critical"]["status"] == "ok"
    assert payload["contracts"]["photo_critical"]["status"] == "ok"
    assert payload["contracts"]["route_critical"]["status"] == "ok"
    assert payload["raw_summary"]["missing_total"] == 0
    assert "checked_at" in payload
    assert "alembic_version" in payload


def test_db_schema_diagnostics_includes_alembic_version_new(client: TestClient) -> None:
    payload = client.get("/admin/diagnostics/db-schema").json()
    assert "alembic_version" in payload
    if payload["alembic_version"] is not None:
        assert isinstance(payload["alembic_version"], str)
        assert len(payload["alembic_version"]) >= 8


def test_db_schema_diagnostics_response_shape_stable_new(client: TestClient) -> None:
    payload = client.get("/admin/diagnostics/db-schema").json()
    assert set(payload) == {"status", "alembic_version", "checked_at", "contracts", "raw_summary"}
    contract = payload["contracts"]["import_critical"]
    assert set(contract) == {"status", "missing_tables", "missing_columns", "existing_tables", "existing_columns", "extra_info"}
    assert set(payload["raw_summary"]) == {"tables_checked", "columns_checked", "missing_total"}


def test_db_schema_diagnostics_does_not_accept_post_new(client: TestClient) -> None:
    response = client.post("/admin/diagnostics/db-schema", json={"sql": "select 1"})
    assert response.status_code == 405


def test_evaluate_contract_reports_missing_table_new() -> None:
    result = evaluate_contract(
        IMPORT_CRITICAL,
        existing_tables={"places"},
        existing_columns={"places": {"id", "city_id"}},
    )
    assert result["status"] == "schema_drift"
    assert "city_import_scopes" in result["missing_tables"]
    assert "place_field_provenance" in result["missing_tables"]


def test_evaluate_contract_reports_missing_column_new() -> None:
    result = evaluate_contract(
        IMPORT_CRITICAL,
        existing_tables=set(IMPORT_CRITICAL.tables),
        existing_columns={table: set(columns) for table, columns in IMPORT_CRITICAL.columns.items() if table != "places"}
        | {"places": {"id", "city_id", "slug", "title"}},
    )
    assert result["status"] == "schema_drift"
    assert "places.place_layer" in result["missing_columns"]
    assert "places.primary_destination_id" in result["missing_columns"]


def test_contract_groups_cover_import_photo_route_new() -> None:
    keys = {IMPORT_CRITICAL.key, PHOTO_CRITICAL.key, ROUTE_CRITICAL.key}
    assert keys == {"import_critical", "photo_critical", "route_critical"}
    assert "place_field_provenance" in IMPORT_CRITICAL.tables
    assert "place_images" in PHOTO_CRITICAL.tables
    assert "places" in ROUTE_CRITICAL.columns
