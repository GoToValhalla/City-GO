"""Dry-run address recovery с экспортом review."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from models.place import Place
from services.place_address_geocode import (
    ReverseGeocodeCandidate,
    format_nominatim_address,
    reverse_geocode_candidate,
    reverse_geocode_payload,
)
from services.place_address_recovery_assess import assess_proposed_address
from services.place_address_recovery_candidates import recovery_candidates
from services.place_address_recovery_export import build_summary, export_review

_ORIGINAL_REVERSE_GEOCODE_PAYLOAD = reverse_geocode_payload


def run_recovery_dry_run(
    db: Session,
    *,
    city_slug: str,
    limit: int,
    sleep_seconds: float,
    export_review_files: bool,
    include_generic: bool = False,
) -> dict[str, Any]:
    city, places = recovery_candidates(db, city_slug, limit, include_generic=include_generic)
    rows: list[dict[str, object]] = []
    errors = 0
    provider_counts: dict[str, int] = {}
    for place in places:
        row, row_errors = _recover_row(place, city.name, city.slug)
        rows.append(row)
        errors += row_errors
        provider = str(row.get("source") or "")
        if provider:
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        time.sleep(sleep_seconds)
    summary = build_summary(city_slug, rows, errors, 0)
    files = export_review(city_slug, rows, summary) if export_review_files else {}
    return {
        **summary,
        "mode": "dry_run",
        "review_files": files,
        "include_generic": include_generic,
        "providers": provider_counts,
    }


def _resolve_candidate(place: Place) -> ReverseGeocodeCandidate | None:
    """Support legacy payload stubs while production uses the provider cascade."""
    if reverse_geocode_payload is not _ORIGINAL_REVERSE_GEOCODE_PAYLOAD:
        payload = reverse_geocode_payload(float(place.lat), float(place.lng))
        address = format_nominatim_address(payload)
        if not address:
            return None
        return ReverseGeocodeCandidate(
            address,
            "nominatim_reverse",
            0.75,
            "building" if (payload.get("address") or {}).get("house_number") else "street",
            raw_payload=payload,
        )
    return reverse_geocode_candidate(float(place.lat), float(place.lng), category=place.category)


def _recover_row(place: Place, city_name: str, city_slug: str) -> tuple[dict[str, object], int]:
    base = _base_row(place)
    if place.lat is None or place.lng is None:
        return {**base, "skip_reason": "no_coordinates", "comment": "Нет координат"}, 0
    try:
        candidate = _resolve_candidate(place)
        proposed = candidate.address if candidate else None
        assessment = assess_proposed_address(proposed, place.category, city_name=city_name, city_slug=city_slug)
        raw_display_name = ""
        if candidate and isinstance(candidate.raw_payload, dict):
            raw_display_name = str(candidate.raw_payload.get("display_name") or "")
        return {
            **base,
            "proposed_address": proposed or "",
            "source": candidate.source if candidate else "",
            "provider_confidence": candidate.confidence if candidate else 0,
            "precision": candidate.precision if candidate else "unknown",
            "distance_meters": candidate.distance_meters if candidate else None,
            "raw_display_name": raw_display_name,
            **assessment,
        }, 0
    except Exception as exc:
        return {
            **base,
            "skip_reason": "error",
            "comment": str(exc),
            "confidence": "none",
        }, 1


def _base_row(place: Place) -> dict[str, object]:
    return {
        "place_id": place.id,
        "slug": place.slug,
        "title": place.title,
        "category": place.category,
        "lat": place.lat,
        "lng": place.lng,
        "old_address": place.address or "",
        "proposed_address": "",
        "source": "",
        "confidence": "none",
        "provider_confidence": 0,
        "precision": "unknown",
        "distance_meters": None,
        "raw_display_name": "",
        "should_apply": False,
        "skip_reason": "",
        "comment": "",
    }
