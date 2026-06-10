"""Parse enriched CSV cell values into Python types."""
from __future__ import annotations

import json


def is_empty(value: str | None) -> bool:
    return value is None or str(value).strip() == ""


def parse_bool(value: str) -> bool | None:
    v = value.strip().lower()
    if v in ("1", "true", "yes", "да"):
        return True
    if v in ("0", "false", "no", "нет"):
        return False
    return None


def parse_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def parse_opening_hours(value: str) -> dict[str, object] | str | None:
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else raw
        except json.JSONDecodeError:
            return raw
    return {"raw": raw, "source": "enrichment_import"}


def parse_field(column: str, value: str) -> object | None:
    if is_empty(value):
        return None
    if column in ("suggested_dog_friendly", "suggested_family_friendly",
                  "suggested_outdoor", "suggested_indoor"):
        return parse_bool(value)
    if column == "suggested_price_level":
        return parse_int(value)
    if column == "suggested_opening_hours":
        return parse_opening_hours(value)
    return value.strip()
