from __future__ import annotations

from datetime import datetime

from services.place_staleness_policy import staleness_penalty

LABELS = {"high": 1.0, "medium": 0.78, "low": 0.5}


def data_confidence_score(place: object, now: datetime | None = None) -> float:
    base = _confidence_value(getattr(place, "confidence", None))
    stale = staleness_penalty(place, now)
    return max(0.0, min(1.0, base - stale))


def _confidence_value(value: object) -> float:
    numeric = _numeric_confidence(value)
    if numeric is not None:
        return numeric
    normalized = str(value or "").strip().casefold()
    return LABELS.get(normalized, 0.72)


def _numeric_confidence(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return _float_confidence(float(value))


def _float_confidence(value: float) -> float:
    if value <= 1.0:
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, value / 100.0))
