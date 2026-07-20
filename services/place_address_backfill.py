"""Backfill и перепроверка адресов через каскад reverse geocoding."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_address_geocode import ReverseGeocodeCandidate, reverse_geocode, reverse_geocode_candidate
from services.place_address_policy import PLACEHOLDER_ADDRESSES, is_real_address, needs_backfill, should_apply_geocode_result
from services.place_change_review_service import propose_place_change
from services.place_import_lifecycle_service import mark_place_for_review
from services.place_verification_mutation import transition_place_verification

ADDRESS_MATCH_THRESHOLD = 0.72
_ORIGINAL_REVERSE_GEOCODE = reverse_geocode
# Hard wall-clock cap for one run_backfill() call. Per-request geocode timeouts
# alone don't bound total runtime: up to `limit` (often thousands) places times
# a deliberate sleep_seconds throttle plus per-request timeout could otherwise
# run for many hours with no final result — the same class of risk fixed for
# photo enrichment (data/scripts/enrich_place_images.py MAX_RUNTIME_SECONDS).
MAX_RUNTIME_SECONDS = 10 * 60


def run_backfill(
    db: Session,
    *,
    city_slug: str,
    limit: int,
    sleep_seconds: float,
    apply: bool,
    verify_existing: bool = False,
    start_after_id: int = 0,
) -> dict[str, Any]:
    stats = _empty_stats(city_slug, apply, verify_existing, start_after_id)
    deadline = time.monotonic() + MAX_RUNTIME_SECONDS
    for place in _iter_candidate_places(db, city_slug, verify_existing=verify_existing, start_after_id=start_after_id):
        if stats["checked"] >= limit:
            break
        if time.monotonic() >= deadline:
            stats["deadline_exceeded"] = True
            stats["warnings"].append(f"Stopped after exceeding max runtime of {MAX_RUNTIME_SECONDS}s; checked {stats['checked']} places.")
            break
        stats["last_scanned_place_id"] = int(place.id)
        _process_place(db, place, stats, sleep_seconds, apply, verify_existing)
    return stats


def _empty_stats(city_slug: str, apply: bool, verify_existing: bool, start_after_id: int) -> dict[str, Any]:
    return {
        "mode": "apply" if apply else "dry_run",
        "city": city_slug,
        "verify_existing": verify_existing,
        "start_after_id": start_after_id,
        "last_scanned_place_id": start_after_id,
        "checked": 0,
        "updated": 0,
        "verified_existing": 0,
        "sent_to_review": 0,
        "skipped_no_coordinates": 0,
        "skipped_generic_result": 0,
        "skipped_existing_address": 0,
        "cleared_placeholders": 0,
        "errors": 0,
        "providers": {},
        "deadline_exceeded": False,
        "warnings": [],
        "updated_place_ids": [],
        "results": [],
    }


def _needs_backfill_sql():
    placeholders = [value for value in PLACEHOLDER_ADDRESSES if value]
    clauses = [Place.address.is_(None), Place.address == ""]
    if placeholders:
        clauses.append(Place.address.in_(placeholders))
    clauses.append(Place.address.ilike("координаты%"))
    return or_(*clauses)


def _iter_candidate_places(db: Session, city_slug: str, *, verify_existing: bool, start_after_id: int = 0, page_size: int = 50):
    last_id = int(start_after_id or 0)
    while True:
        query = db.query(Place).join(City).filter(City.slug == city_slug, Place.id > last_id)
        if not verify_existing:
            query = query.filter(_needs_backfill_sql())
        page = query.order_by(Place.id.asc()).limit(page_size).all()
        if not page:
            return
        for place in page:
            last_id = int(place.id)
            yield place


def _resolve_candidate(place: Place) -> ReverseGeocodeCandidate | None:
    """Keep the legacy hook available while production uses the provider cascade."""
    if reverse_geocode is not _ORIGINAL_REVERSE_GEOCODE:
        address = reverse_geocode(float(place.lat), float(place.lng))
        if not address:
            return None
        return ReverseGeocodeCandidate(address, "nominatim_reverse", 0.75, "street")
    return reverse_geocode_candidate(float(place.lat), float(place.lng), category=place.category)


def _process_place(db: Session, place: Place, stats: dict[str, Any], sleep_seconds: float, apply: bool, verify_existing: bool) -> None:
    has_existing_real_address = is_real_address(place.address)
    if has_existing_real_address and not verify_existing:
        stats["skipped_existing_address"] += 1
        return
    if not has_existing_real_address and not needs_backfill(place.address):
        stats["skipped_existing_address"] += 1
        return
    if place.lat is None or place.lng is None:
        stats["skipped_no_coordinates"] += 1
        return

    stats["checked"] += 1
    try:
        candidate = _resolve_candidate(place)
    except Exception as exc:
        stats["errors"] += 1
        _append_result(stats, place, "error", error=str(exc))
        time.sleep(sleep_seconds)
        return

    if candidate is None or not should_apply_geocode_result(candidate.address, place.category):
        stats["skipped_generic_result"] += 1
        if apply and not has_existing_real_address:
            _clear_placeholder(db, place, stats)
        _append_result(stats, place, "skipped_generic", old_address=place.address, new_address=candidate.address if candidate else None)
        time.sleep(sleep_seconds)
        return

    providers = stats["providers"]
    providers[candidate.source] = int(providers.get(candidate.source) or 0) + 1
    old_address = place.address
    if has_existing_real_address:
        if addresses_match(old_address, candidate.address):
            if apply:
                _mark_existing_address_verified(db, place, candidate.source, candidate.confidence)
            stats["verified_existing"] += 1
            _append_result(stats, place, "verified_existing", old_address=old_address, new_address=candidate.address)
        else:
            if apply:
                _mark_address_for_review(db, place, candidate.address, candidate.source)
            stats["sent_to_review"] += 1
            _append_result(stats, place, "sent_to_review", old_address=old_address, new_address=candidate.address)
        time.sleep(sleep_seconds)
        return

    if apply:
        place.address = candidate.address
        place.address_source = candidate.source
        place.address_confidence = candidate.confidence
        place.address_updated_at = datetime.utcnow()
        mark_place_for_review(place, reason="address_enriched")
        db.add(place)
        db.commit()
        stats["updated"] += 1
        stats["updated_place_ids"].append(int(place.id))
    else:
        stats["updated"] += 1
    _append_result(
        stats,
        place,
        "updated" if apply else "dry_run",
        old_address=old_address,
        new_address=candidate.address,
        source=candidate.source,
        confidence=candidate.confidence,
        precision=candidate.precision,
    )
    time.sleep(sleep_seconds)


def addresses_match(current: str | None, candidate: str | None) -> bool:
    current_tokens = _address_tokens(current)
    candidate_tokens = _address_tokens(candidate)
    if not current_tokens or not candidate_tokens:
        return False
    score = len(current_tokens & candidate_tokens) / max(len(current_tokens), len(candidate_tokens))
    if score >= ADDRESS_MATCH_THRESHOLD:
        return True
    return bool(_digits(current) and _digits(candidate) and _digits(current) == _digits(candidate) and (current_tokens & candidate_tokens))


def _address_tokens(value: str | None) -> set[str]:
    normalized = str(value or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[,.()\[\]{}:;№#]", " ", normalized)
    stop_words = {"город", "ул", "улица", "пр", "проспект", "пер", "переулок", "дом", "район", "область", "рядом", "с"}
    return {token for token in re.split(r"\s+", normalized) if token and len(token) > 1 and token not in stop_words}


def _digits(value: str | None) -> set[str]:
    return set(re.findall(r"\d+[а-яa-z]?", str(value or "").casefold()))


def _mark_existing_address_verified(db: Session, place: Place, source: str, confidence: float) -> None:
    place.address_source = place.address_source or f"{source}_verified"
    place.address_confidence = max(float(place.address_confidence or 0), confidence)
    place.address_updated_at = datetime.utcnow()
    db.add(place)
    db.commit()


def _mark_address_for_review(db: Session, place: Place, candidate: str, source: str) -> None:
    comment = f"Конфликт адреса. Текущий: {place.address or ''}. Кандидат: {candidate or ''}."[:1000]
    transition_place_verification(
        db,
        place,
        to_status="needs_recheck",
        actor="place_address_backfill",
        reason=comment,
        verification_source=source,
        verification_method="address_conflict",
    )
    db.commit()


def _clear_placeholder(db: Session, place: Place, stats: dict[str, Any]) -> None:
    if is_real_address(place.address):
        return
    if not propose_place_change(db, place=place, proposed={"address": ""}, reason="placeholder_address_cleared"):
        db.commit()
        return
    place.address = ""
    place.updated_at = datetime.utcnow()
    db.add(place)
    db.commit()
    stats["cleared_placeholders"] += 1


def _append_result(stats: dict[str, Any], place: Place, status: str, **extra: object) -> None:
    if stats.get("mode") == "apply":
        return
    stats["results"].append({"place_id": place.id, "title": place.title, "status": status, **extra})
