from __future__ import annotations

import hashlib
import json
from typing import Any

PRODUCT_PUBLICATION_FIELDS = {
    "is_published",
    "is_visible_in_catalog",
    "is_route_eligible",
    "is_searchable",
    "publication_status",
    "published_at",
    "unpublished_at",
}


def build_import_idempotency_key(*, provider: str, external_id: str, payload_hash: str) -> str:
    """Build deterministic import idempotency key for raw observations."""

    raw = f"{provider}:{external_id}:{payload_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def payload_hash(payload: dict[str, Any]) -> str:
    """Stable hash for provider payloads."""

    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assert_import_update_does_not_touch_publication_state(update_fields: set[str]) -> None:
    """Guard Stage 2 import writes from mutating product publication fields."""

    forbidden = PRODUCT_PUBLICATION_FIELDS.intersection(update_fields)
    if forbidden:
        raise ValueError(f"Import update cannot mutate publication state: {sorted(forbidden)}")
