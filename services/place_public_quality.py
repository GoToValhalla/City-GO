from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

EMPTY_STRINGS = {"", "null", "undefined", "none", "nan"}


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in EMPTY_STRINGS else text


def first_image(place: Any, image_urls: list[str] | None) -> str | None:
    return (image_urls or [_clean(getattr(place, "image_url", None)) or None])[0]


def hours_text(value: object) -> object | None:
    if isinstance(value, dict):
        return _clean(value.get("display") or value.get("raw")) or value
    return _clean(value)


def quality_payload(place: Any, lineage: dict[str, dict[str, object]], coord_degraded: bool) -> dict[str, object]:
    score = int(getattr(place, "completeness_score", 0) or 0)
    return {
        "is_degraded": coord_degraded or score < 20,
        "completeness_score": score,
        "source_freshness_days": freshness_days(lineage),
    }


def freshness_days(lineage: dict[str, dict[str, object]]) -> int | None:
    dates = [datetime.fromisoformat(str(item["updated_at"])) for item in lineage.values() if item.get("updated_at")]
    if not dates:
        return None
    newest = max(date if date.tzinfo else date.replace(tzinfo=timezone.utc) for date in dates)
    return max(0, (datetime.now(timezone.utc) - newest).days)
