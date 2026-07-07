"""Pydantic models for admin DB schema diagnostics."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SchemaContractDiagnostics(BaseModel):
    status: Literal["ok", "schema_drift"]
    missing_tables: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)
    existing_tables: list[str] = Field(default_factory=list)
    existing_columns: list[str] = Field(default_factory=list)
    extra_info: dict[str, object] = Field(default_factory=dict)


class DbSchemaRawSummary(BaseModel):
    tables_checked: int
    columns_checked: int
    missing_total: int


class AdminDbSchemaDiagnosticsResponse(BaseModel):
    status: Literal["ok", "schema_drift"]
    alembic_version: str | None
    checked_at: str
    contracts: dict[str, SchemaContractDiagnostics]
    raw_summary: DbSchemaRawSummary
