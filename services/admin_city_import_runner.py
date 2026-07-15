"""Запуск OSM-импорта для города через run_due_import_jobs."""

from __future__ import annotations

from collections import Counter
from typing import Any

from data.scripts.run_due_import_jobs import run as run_due_import_jobs
from services.import_pipeline.scope_errors import scope_failure_rows

_FUNNEL_SUM_FIELDS = (
    "requested",
    "fetched",
    "normalized",
    "accepted",
    "matched_existing",
    "created",
    "updated",
    "unchanged",
    "hidden",
    "sent_to_review",
    "failed",
)


def run_city_import_targets(city_slug: str, *, force: bool = True, city_admin_import_job_id: int | None = None) -> dict[str, Any]:
    """Импортирует все scopes города (apply)."""
    base = ["--apply", "--city", city_slug]
    if force:
        base.append("--force")
    if city_admin_import_job_id is not None:
        base.extend(["--city-admin-import-job-id", str(city_admin_import_job_id)])
    return run_due_import_jobs(base)


def run_osm_import_only(city_slug: str, *, force: bool = True, city_admin_import_job_id: int | None = None) -> dict[str, Any]:
    """Только OSM-импорт без адресов и quality cleanup (для пошагового pipeline)."""
    base = [
        "--apply",
        "--city",
        city_slug,
        "--skip-address-backfill",
        "--skip-image-enrichment",
        "--skip-quality-cleanup",
    ]
    if force:
        base.append("--force")
    if city_admin_import_job_id is not None:
        base.extend(["--city-admin-import-job-id", str(city_admin_import_job_id)])
    return run_due_import_jobs(base)


def summarize_import_results(payload: dict[str, Any]) -> dict[str, int | str | None | list[dict[str, object]]]:
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    scope_errors = scope_failure_rows(results)
    counters = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "needs_review": 0,
        "hidden": 0,
        "hidden_missing_places": 0,
        "missing_from_source": 0,
        "rejected": 0,
    }
    scopes_total = len(results)
    scopes_succeeded = sum(1 for row in results if row.get("status") == "success")
    places_found = 0
    errors: list[str] = []

    funnel: dict[str, int | str] = {field: 0 for field in _FUNNEL_SUM_FIELDS}
    rejected_by_reason: Counter[str] = Counter()
    any_scope_reported_funnel = False
    deduplicated_total = 0
    any_scope_reported_dedup_available = False

    for row in results:
        if row.get("status") != "success":
            reason = str(row.get("error") or row.get("reason") or row.get("status") or "unknown")
            errors.append(f"{row.get('scope')}: {reason}")
            continue
        import_result = row.get("import_result") if isinstance(row.get("import_result"), dict) else {}
        fallback_result = import_result.get("fallback_result") if isinstance(import_result.get("fallback_result"), dict) else {}
        fallback_import = fallback_result.get("import_result") if isinstance(fallback_result.get("import_result"), dict) else {}
        # The bbox-expansion fallback (run_due_import_jobs._run_expanded_bbox_fallback)
        # runs _apply_import a SECOND time against a fresh ImportBatch — it never
        # replaces the original run's already-committed Place/SourceObservation/
        # review-queue rows, it adds to them (create_batch always inserts a new
        # ImportBatch row; see services/import_job_service.py). Both runs' counters
        # are therefore real, independently persisted facts and must be SUMMED, not
        # have one silently discard the other. Picking only the fallback's result
        # (as this used to do) meant a near-empty fallback silently zeroed out a
        # genuinely successful original run's created/updated/needs_review counts
        # in the displayed summary, even though those rows were still in the
        # database — exactly the found=136/saved=0 production defect this fixes.
        places_found += int(import_result.get("raw_count") or 0) + int(fallback_import.get("raw_count") or 0)
        for key in counters:
            counters[key] += int(import_result.get(key) or 0) + int(fallback_import.get(key) or 0)

        # Funnel: same additive-across-scopes rule as the counters above —
        # each scope's (and its fallback's) funnel is a real, independently
        # produced fact from _apply_import, summed here, never recomputed.
        for scope_funnel in (import_result.get("funnel"), fallback_import.get("funnel")):
            if not isinstance(scope_funnel, dict):
                continue
            any_scope_reported_funnel = True
            for field in _FUNNEL_SUM_FIELDS:
                funnel[field] = int(funnel[field]) + int(scope_funnel.get(field) or 0)
            reasons = scope_funnel.get("rejected_by_reason")
            if isinstance(reasons, dict):
                for reason_key, count in reasons.items():
                    rejected_by_reason[str(reason_key)] += int(count or 0)
            # "unavailable" is the only value _apply_import ever reports for
            # deduplicated (no dedup step exists in this pipeline) — if any
            # scope ever reports a real number instead, that becomes
            # available; until then this stays "unavailable", never 0.
            scope_dedup = scope_funnel.get("deduplicated")
            if isinstance(scope_dedup, (int, float)) and not isinstance(scope_dedup, bool):
                any_scope_reported_dedup_available = True
                deduplicated_total += int(scope_dedup)

    if any_scope_reported_funnel:
        funnel["deduplicated"] = deduplicated_total if any_scope_reported_dedup_available else "unavailable"
        funnel["rejected_by_reason"] = dict(rejected_by_reason)
    else:
        # No successful scope ever produced a funnel (e.g. every scope
        # failed before reaching _apply_import) — the funnel itself is
        # unavailable, not a truthful all-zero accounting.
        funnel = {field: "unavailable" for field in _FUNNEL_SUM_FIELDS}
        funnel["deduplicated"] = "unavailable"
        funnel["rejected_by_reason"] = {}

    places_saved = counters["created"] + counters["updated"] + counters["needs_review"]
    meaningful_changes = (
        places_saved
        + counters["hidden"]
        + counters["hidden_missing_places"]
    )
    last_error = "; ".join(errors) if errors else None
    if scopes_total == 0 or scopes_succeeded == 0:
        status = "failed"
    elif errors:
        status = "partial_success" if meaningful_changes > 0 else "failed"
    else:
        status = "success"

    return {
        "scopes_total": scopes_total,
        "scopes_succeeded": scopes_succeeded,
        "places_found": places_found,
        "places_saved": places_saved,
        "meaningful_changes": meaningful_changes,
        **counters,
        "status": status,
        "last_error": last_error,
        "scope_errors": scope_errors,
        "funnel": funnel,
    }
