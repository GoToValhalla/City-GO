from __future__ import annotations


COUNTER_KEYS = (
    "scopes_total", "scopes_processed", "candidates_found", "places_created",
    "places_updated", "duplicates_skipped", "memberships_created",
    "memberships_updated", "review_items_created", "enrichment_tasks_created",
    "safe_merges_applied", "service_only_hidden", "errors_count", "source_errors",
)


def empty_counters() -> dict[str, int]:
    return {key: 0 for key in COUNTER_KEYS}


def add_counter(counters: dict[str, int], key: str, value: int = 1) -> None:
    counters[key] = int(counters.get(key, 0)) + value
