from __future__ import annotations

from datetime import datetime, timedelta


class ProjectionFreshnessError(ValueError):
    pass


class ExtractionReadinessError(ValueError):
    pass


def assert_projection_fresh(*, built_at: datetime | None, max_age_minutes: int, now: datetime | None = None) -> None:
    if built_at is None:
        raise ProjectionFreshnessError("Projection was never built")
    current_time = now or datetime.utcnow()
    if current_time - built_at > timedelta(minutes=max_age_minutes):
        raise ProjectionFreshnessError("Projection is stale")


def assert_projection_reads_snapshot(*, source_snapshot_version: int | None) -> None:
    if not source_snapshot_version or source_snapshot_version < 1:
        raise ProjectionFreshnessError("Projection requires source snapshot version")


def assert_extraction_ready(
    *,
    owner: str | None,
    api_contract_ref: str | None,
    event_contract_ref: str | None,
    data_migration_plan_ref: str | None,
    rollback_plan_ref: str | None,
) -> None:
    missing = []
    if not owner:
        missing.append("owner")
    if not api_contract_ref:
        missing.append("api_contract_ref")
    if not event_contract_ref:
        missing.append("event_contract_ref")
    if not data_migration_plan_ref:
        missing.append("data_migration_plan_ref")
    if not rollback_plan_ref:
        missing.append("rollback_plan_ref")
    if missing:
        raise ExtractionReadinessError(f"Extraction is not ready: missing {', '.join(missing)}")
