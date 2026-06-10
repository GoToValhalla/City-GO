"""Dry-run address recovery с экспортом review."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from models.place import Place
from services.place_address_geocode import format_nominatim_address, reverse_geocode_payload
from services.place_address_recovery_assess import assess_proposed_address
from services.place_address_recovery_candidates import recovery_candidates
from services.place_address_recovery_export import build_summary, export_review


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
    http_403 = 0
    for place in places:
        row, row_errors, row_403 = _recover_row(place, city.name, city.slug)
        rows.append(row)
        errors += row_errors
        http_403 += row_403
        time.sleep(sleep_seconds)
    summary = build_summary(city_slug, rows, errors, http_403)
    files = export_review(city_slug, rows, summary) if export_review_files else {}
    return {**summary, "mode": "dry_run", "review_files": files, "include_generic": include_generic}


def _recover_row(place: Place, city_name: str, city_slug: str) -> tuple[dict[str, object], int, int]:
    base = _base_row(place)
    if place.lat is None or place.lng is None:
        return {**base, "skip_reason": "no_coordinates", "comment": "Нет координат"}, 0, 0
    try:
        payload = reverse_geocode_payload(float(place.lat), float(place.lng))
        proposed = format_nominatim_address(payload)
        assessment = assess_proposed_address(
            proposed, place.category, city_name=city_name, city_slug=city_slug,
        )
        return {
            **base,
            "proposed_address": proposed or "",
            "source": "nominatim_reverse",
            "raw_display_name": str(payload.get("display_name") or ""),
            **assessment,
        }, 0, 0
    except Exception as exc:
        err_text = str(exc)
        return {
            **base,
            "skip_reason": "error",
            "comment": err_text,
            "confidence": "none",
        }, 1, 1 if "403" in err_text else 0


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
        "raw_display_name": "",
        "should_apply": False,
        "skip_reason": "",
        "comment": "",
    }
