"""Map eligibility/policy failures to one canonical primary publication reason code."""

from __future__ import annotations

from collections.abc import Iterable

from services.publication_state_writer import (
    REASON_DUPLICATE_SUSPECTED,
    REASON_MISSING_COORDINATES,
    REASON_NON_PUBLIC_CATEGORY,
    REASON_POLICY_GATE_FAILED,
    REASON_SPAM_SUSPECTED,
)


def primary_publication_reason(reasons: Iterable[object]) -> str:
    normalized = " ".join(str(reason).strip().lower() for reason in reasons)
    if "missing_coordinates" in normalized or "coordinate" in normalized or " lat" in normalized or " lng" in normalized:
        return REASON_MISSING_COORDINATES
    if "duplicate" in normalized:
        return REASON_DUPLICATE_SUSPECTED
    if "spam" in normalized:
        return REASON_SPAM_SUSPECTED
    if any(token in normalized for token in ("category", "layer", "service", "transport", "public_hidden")):
        return REASON_NON_PUBLIC_CATEGORY
    return REASON_POLICY_GATE_FAILED
