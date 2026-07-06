from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

SourceName = Literal["MANUAL", "EDITORIAL_CLEANSED", "EXTERNAL_API_ENRICHED", "OSM_INGESTION", "UNKNOWN"]

SOURCE_PRIORITIES: dict[str, int] = {
    "MANUAL": 100,
    "EDITORIAL_CLEANSED": 80,
    "EXTERNAL_API_ENRICHED": 50,
    "OSM_INGESTION": 20,
    "UNKNOWN": 0,
}


class LineageEntry(BaseModel):
    source: SourceName = "UNKNOWN"
    updated_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = Field(ge=0)

    @field_validator("updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")
        return value


def source_priority(source: str | None) -> int:
    return SOURCE_PRIORITIES.get((source or "UNKNOWN").upper(), 0)


def normalize_source(source: str | None) -> SourceName:
    normalized = (source or "UNKNOWN").upper()
    return normalized if normalized in SOURCE_PRIORITIES else "UNKNOWN"  # type: ignore[return-value]


def lineage_entry(source: str | None, confidence: float) -> dict[str, object]:
    normalized = normalize_source(source)
    return LineageEntry(
        source=normalized,
        updated_at=datetime.now(timezone.utc),
        confidence=confidence,
        priority=source_priority(normalized),
    ).model_dump(mode="json")


def validate_lineage_map(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict):
        raise ValueError("lineage must be an object")
    return {str(key): LineageEntry.model_validate(raw).model_dump(mode="json") for key, raw in value.items()}


def safe_lineage_map(value: object) -> dict[str, dict[str, object]]:
    try:
        return validate_lineage_map(value)
    except (TypeError, ValueError, ValidationError):
        return {}
