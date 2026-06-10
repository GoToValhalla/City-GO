"""Запуск OSM-импорта для города через run_due_import_jobs."""

from __future__ import annotations

from typing import Any

from data.scripts.run_due_import_jobs import run as run_due_import_jobs


def run_city_import_targets(city_slug: str, *, force: bool = True) -> dict[str, Any]:
    """Импортирует все scopes города (apply)."""
    return run_due_import_jobs(["--apply", "--city", city_slug, "--force"] if force else ["--apply", "--city", city_slug])


def run_osm_import_only(city_slug: str, *, force: bool = True) -> dict[str, Any]:
    """Только OSM-импорт без адресов и quality cleanup (для пошагового pipeline)."""
    base = ["--apply", "--city", city_slug, "--skip-address-backfill", "--skip-quality-cleanup"]
    return run_due_import_jobs(base + ["--force"] if force else base)


def summarize_import_results(payload: dict[str, Any]) -> dict[str, int | str | None]:
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    scopes_total = len(results)
    scopes_succeeded = sum(1 for row in results if row.get("status") == "success")
    places_found = 0
    places_saved = 0
    errors: list[str] = []
    for row in results:
        if row.get("status") != "success":
            reason = str(row.get("error") or row.get("reason") or row.get("status") or "unknown")
            errors.append(f"{row.get('scope')}: {reason}")
            continue
        import_result = row.get("import_result") if isinstance(row.get("import_result"), dict) else {}
        places_found += int(import_result.get("raw_count") or 0)
        places_saved += int(import_result.get("created") or 0) + int(import_result.get("updated") or 0)
    last_error = "; ".join(errors) if errors else None
    if scopes_total == 0 or scopes_succeeded == 0 or errors:
        status = "failed"
    else:
        status = "success"
    return {
        "scopes_total": scopes_total,
        "scopes_succeeded": scopes_succeeded,
        "places_found": places_found,
        "places_saved": places_saved,
        "status": status,
        "last_error": last_error,
    }
