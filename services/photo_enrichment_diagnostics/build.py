"""Structured photo enrichment diagnostics for admin import surfaces."""

from __future__ import annotations

from models.city import City
from services.photo_enrichment_diagnostics.eligibility import (
    eligible_for_photo_search,
    filtered_out_by_reason,
    pending_photos_existing,
    without_photo_total,
)
from services.photo_enrichment_diagnostics.provider_state import admin_hint, provider_state
from sqlalchemy.orm import Session

_PROVIDER_MODE = "trusted_source_evidence_plus_commons_and_openverse_search"


def build_photo_enrichment_diagnostics(
    db: Session,
    city: City,
    *,
    enrichment_result: dict[str, object] | None = None,
    step_status: str | None = None,
    dependency_step: str | None = None,
    scan_limit: int | None = None,
) -> dict[str, object]:
    city_id = int(city.id)
    without_photo = without_photo_total(db, city_id=city_id)
    eligible = eligible_for_photo_search(db, city_id=city_id)
    pending_existing = pending_photos_existing(db, city_id=city_id)
    run = enrichment_result if isinstance(enrichment_result, dict) else {}
    created = int(run.get("created") or 0)
    scanned = int(run.get("scanned_places") or 0)
    pool_total = int(run.get("places_without_public_image_total") or eligible)
    filtered_run = _filtered_from_run(run, scan_limit=scan_limit, pool_total=pool_total, scanned=scanned)
    filtered_db = filtered_out_by_reason(db, city_id=city_id)
    filtered_out = {**filtered_db, **filtered_run}
    filtered_total = sum(int(value) for value in filtered_out.values())
    provider_status, zero_reason, provider_warning, provider_error = provider_state(
        run,
        without_photo=without_photo,
        eligible=eligible,
        created=created,
        scanned=scanned,
        step_status=step_status,
        dependency_step=dependency_step,
    )
    step = step_status or ("success" if created > 0 else ("failed" if provider_error else "warning"))
    diagnostics: dict[str, object] = {
        "without_photo_total": without_photo,
        "eligible_for_photo_search": eligible,
        "pending_photos_created": created,
        "pending_photos_existing": pending_existing,
        "filtered_out_total": filtered_total,
        "filtered_out_by_reason": filtered_out,
        "provider_status": provider_status,
        "provider_warning": provider_warning,
        "provider_error": provider_error,
        "zero_result_reason": zero_reason,
        "step_status": step,
        "admin_hint": admin_hint(provider_status, without_photo, created, pending_existing, zero_reason),
        "provider_mode": run.get("provider_mode") or _PROVIDER_MODE,
        "scanned_places": scanned,
        "candidates_found": int(run.get("candidates_found") or 0),
    }
    if without_photo > 0 and created == 0 and pending_existing == 0 and not zero_reason:
        diagnostics["zero_result_reason"] = "unknown_zero_result"
        diagnostics["provider_warning"] = diagnostics["provider_warning"] or "Добор фото не создал кандидатов, причина не записана."
    return diagnostics


def attach_photo_diagnostics_to_summary(db: Session, city: City, summary: dict[str, object], *, scan_limit: int | None = None) -> dict[str, object]:
    diagnostics = build_photo_enrichment_diagnostics(db, city, enrichment_result=summary, scan_limit=scan_limit)
    return {**summary, "photo_diagnostics": diagnostics}


def _filtered_from_run(run: dict[str, object], *, scan_limit: int | None, pool_total: int, scanned: int) -> dict[str, int]:
    mapped = {
        "service_category": int(run.get("skipped_ineligible") or 0),
        "existing_photo": int(run.get("skipped_has_approved") or 0) + int(run.get("skipped_duplicates") or 0),
        "no_source_evidence": int(run.get("skipped_no_source") or 0),
    }
    if scan_limit and pool_total > scanned:
        mapped["limit_reached"] = max(pool_total - scanned, 0)
    return {key: value for key, value in mapped.items() if value > 0}
