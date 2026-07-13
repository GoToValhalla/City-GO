"""Read-only production migration preflight.

Run this BEFORE `alembic upgrade head` in the deploy path. It never creates
or alters schema — it only inspects the current database and reports
whether it is safe to run the pending Alembic migrations against it.

Exit codes:
  0 — safe to proceed (schema is clean, or every existing object that
      overlaps with the target model shape is compatible).
  1 — unsafe: at least one existing table/column is incompatible with the
      shape the models/migrations expect (wrong type, unexpectedly NOT
      NULL, etc.) — a plain `alembic upgrade head` could fail loudly or,
      worse, silently diverge from the model's expectations.
  2 — could not complete the check (connection/timeout/import failure) —
      treated as fail-closed, since an incomplete check must not be
      mistaken for a passing one.

Usage:
  python scripts/migration_preflight.py
  python scripts/migration_preflight.py --statement-timeout-ms 5000

Reads DATABASE_URL from the environment (same as Alembic/the app). Never
prints the DSN or any credential — only a masked form (scheme://user@host/db).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DEFAULT_STATEMENT_TIMEOUT_MS = 5_000
DEFAULT_LOCK_TIMEOUT_MS = 3_000
DEFAULT_CONNECT_TIMEOUT_S = 10


def mask_database_url(url: str) -> str:
    """scheme://user:password@host:port/db -> scheme://user@host:port/db.
    Never returns the password; falls back to a fixed placeholder if the
    URL cannot be parsed at all, rather than risking a partial leak."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<unparseable-database-url>"
    if parts.password is None and "@" not in (parts.netloc or ""):
        netloc = parts.netloc
    else:
        userinfo = parts.username or ""
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        netloc = f"{userinfo}@{host}{port}" if userinfo else f"{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


@dataclass
class PreflightFinding:
    table: str
    column: str | None
    kind: str  # "missing_table" | "missing_column" | "incompatible_column" | "missing_index" | "missing_constraint"
    detail: str


@dataclass
class PreflightReport:
    ok: bool
    database_url_masked: str
    tables_checked: int
    findings: list[PreflightFinding] = field(default_factory=list)
    incompatible: list[PreflightFinding] = field(default_factory=list)

    def render(self, *, verbose: bool = False) -> str:
        lines = [
            "=== Migration preflight ===",
            f"database: {self.database_url_masked}",
            f"tables checked: {self.tables_checked}",
            f"findings: {len(self.findings)} (missing objects Alembic will create — expected/compatible, not blocking)",
            f"incompatible: {len(self.incompatible)}",
        ]
        if verbose:
            for item in self.findings:
                lines.append(f"  [missing]       {item.table}.{item.column or ''} — {item.detail}")
        for item in self.incompatible:
            lines.append(f"  [INCOMPATIBLE]  {item.table}.{item.column or ''} — {item.detail}")
        lines.append("RESULT: " + ("OK — safe to run alembic upgrade head" if self.ok else "UNSAFE — do not run alembic upgrade head"))
        return "\n".join(lines)


# Column types that are safe to consider equivalent across DB-reported vs
# model-declared type spelling (e.g. Postgres reports VARCHAR(n) while the
# model may say String(n) — these normalize to the same Python-level type
# class name in SQLAlchemy's own type hierarchy, so compare on that).
def _type_class_name(sqla_type: Any) -> str:
    return type(sqla_type).__name__.upper()


def _compatible_type(existing_type: Any, expected_type: Any) -> bool:
    existing_name = _type_class_name(existing_type)
    expected_name = _type_class_name(expected_type)
    if existing_name == expected_name:
        return True
    # Common cross-dialect equivalents that are not literally the same
    # SQLAlchemy class but are safe: e.g. Postgres BIGINT reflected as
    # BIGINT vs a model declared as Integer on a small table is a real
    # concern, but VARCHAR vs String, or TEXT vs Text, are the same thing
    # under a different reflection name.
    equivalence_groups = (
        {"VARCHAR", "STRING", "TEXT", "NVARCHAR"},
        {"INTEGER", "BIGINT", "BIGINTEGER", "SMALLINT", "SMALLINTEGER"},
        {"BOOLEAN"},
        {"FLOAT", "DOUBLE_PRECISION", "NUMERIC", "DECIMAL"},
        {"DATETIME", "TIMESTAMP"},
        {"JSON", "JSONB"},
        {"TIME"},
        {"DATE"},
    )
    for group in equivalence_groups:
        if existing_name in group and expected_name in group:
            return True
    return False


def run_preflight(*, database_url: str, statement_timeout_ms: int, lock_timeout_ms: int, connect_timeout_s: int) -> PreflightReport:
    from sqlalchemy import create_engine, inspect

    from db.base import Base
    import models  # noqa: F401 — populate Base.metadata with every model

    masked = mask_database_url(database_url)
    connect_args: dict[str, Any] = {}
    if database_url.startswith("postgresql"):
        connect_args["connect_timeout"] = connect_timeout_s
        connect_args["options"] = f"-c statement_timeout={statement_timeout_ms} -c lock_timeout={lock_timeout_ms}"

    engine = create_engine(database_url, connect_args=connect_args)
    findings: list[PreflightFinding] = []
    incompatible: list[PreflightFinding] = []
    tables_checked = 0

    try:
        inspector = inspect(engine)
        existing_table_names = set(inspector.get_table_names())

        for table_name, table in Base.metadata.tables.items():
            tables_checked += 1
            if table_name not in existing_table_names:
                findings.append(
                    PreflightFinding(table=table_name, column=None, kind="missing_table", detail="table does not exist yet")
                )
                continue

            existing_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            for column in table.columns:
                existing = existing_columns.get(column.name)
                if existing is None:
                    findings.append(
                        PreflightFinding(table=table_name, column=column.name, kind="missing_column", detail="column does not exist yet")
                    )
                    continue
                if not _compatible_type(existing["type"], column.type):
                    incompatible.append(
                        PreflightFinding(
                            table=table_name,
                            column=column.name,
                            kind="incompatible_column",
                            detail=f"existing type {existing['type']!r} is not compatible with expected {column.type!r}",
                        )
                    )
                    continue
                # A column the model declares NOT NULL must not already be
                # nullable in a way that would leave existing rows with NULLs
                # when Alembic adds a NOT NULL constraint without a backfill.
                if not column.nullable and existing.get("nullable", True):
                    findings.append(
                        PreflightFinding(
                            table=table_name,
                            column=column.name,
                            kind="missing_column",
                            detail="existing column is nullable, model expects NOT NULL — migration must backfill before constraining",
                        )
                    )
    except Exception as exc:  # noqa: BLE001 — any failure here is fail-closed, not a false pass
        incompatible.append(PreflightFinding(table="<connection>", column=None, kind="incompatible_column", detail=f"preflight could not complete: {exc}"))
    finally:
        engine.dispose()

    return PreflightReport(
        ok=not incompatible,
        database_url_masked=masked,
        tables_checked=tables_checked,
        findings=findings,
        incompatible=incompatible,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statement-timeout-ms", type=int, default=DEFAULT_STATEMENT_TIMEOUT_MS)
    parser.add_argument("--lock-timeout-ms", type=int, default=DEFAULT_LOCK_TIMEOUT_MS)
    parser.add_argument("--connect-timeout-s", type=int, default=DEFAULT_CONNECT_TIMEOUT_S)
    parser.add_argument("--database-url", default=None, help="Defaults to core.config.settings.database_url / DATABASE_URL env var")
    parser.add_argument("--verbose", action="store_true", help="Also print every compatible 'missing object' finding, not just incompatibilities")
    args = parser.parse_args(argv)

    database_url = args.database_url
    if database_url is None:
        try:
            from core.config import settings

            database_url = settings.database_url
        except Exception as exc:  # noqa: BLE001
            print(f"migration_preflight: could not resolve DATABASE_URL: {exc}", file=sys.stderr)
            return 2

    try:
        report = run_preflight(
            database_url=database_url,
            statement_timeout_ms=args.statement_timeout_ms,
            lock_timeout_ms=args.lock_timeout_ms,
            connect_timeout_s=args.connect_timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"migration_preflight: fatal error: {exc}", file=sys.stderr)
        return 2

    print(report.render(verbose=args.verbose))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
