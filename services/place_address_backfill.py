"""Локальный backfill и перепроверка адресов мест через reverse geocoding."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_address_policy import PLACEHOLDER_ADDRESSES
from services.place_address_geocode import reverse_geocode
from services.place_address_policy import is_real_address, needs_backfill, should_apply_geocode_result

ADDRESS_MATCH_THRESHOLD = 0.72


def run_backfill(
    db: Session,
    *,
    city_slug: str,
    limit: int,
    sleep_seconds: float,
    apply: bool,
    verify_existing: bool = False,
) -> dict[str, Any]:
    stats = _empty_stats(city_slug, apply, verify_existing)
    for place in _iter_candidate_places(db, city_slug, verify_existing=verify_existing):
        if stats["checked"] >= limit:
            break
        _process_place(db, place, stats, sleep_seconds, apply, verify_existing)
    return stats


def _empty_stats(city_slug: str, apply: bool, verify_existing: bool) -> dict[str, Any]:
    return {
        "mode": "apply" if apply else "dry_run",
        "city": city_slug,
        "verify_existing": verify_existing,
        "checked": 0,
        "updated": 0,
        "verified_existing": 0,
        "sent_to_review": 0,
        "skipped_no_coordinates": 0,
        "skipped_generic_result": 0,
        "skipped_existing_address": 0,
        "cleared_placeholders": 0,
        "errors": 0,
        "results": [],
    }


def _needs_backfill_sql():
    placeholders = [value for value in PLACEHOLDER_ADDRESSES if value]
    clauses = [Place.address.is_(None), Place.address == ""]
    if placeholders:
        clauses.append(Place.address.in_(placeholders))
    clauses.append(Place.address.ilike("координаты%"))
    return or_(*clauses)


def _iter_candidate_places(db: Session, city_slug: str, *, verify_existing: bool, page_size: int = 50):
    offset = 0
    while True:
        query = db.query(Place).join(City).filter(City.slug == city_slug)
        if not verify_existing:
            query = query.filter(_needs_backfill_sql())
        page = query.order_by(Place.id.asc()).offset(offset).limit(page_size).all()
        if not page:
            return
        for place in page:
            yield place
        offset += page_size


def _process_place(
    db: Session,
    place: Place,
    stats: dict[str, Any],
    sleep_seconds: float,
    apply: bool,
    verify_existing: bool,
) -> None:
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
        candidate = reverse_geocode(float(place.lat), float(place.lng))
    except Exception as exc:
        stats["errors"] += 1
        _append_result(stats, place, "error", error=str(exc))
        time.sleep(sleep_seconds)
        return

    if not candidate or not should_apply_geocode_result(candidate, place.category):
        stats["skipped_generic_result"] += 1
        if apply and not has_existing_real_address:
            _clear_placeholder(db, place, stats)
        _append_result(stats, place, "skipped_generic", old_address=place.address, new_address=candidate)
        time.sleep(sleep_seconds)
        return

    old_address = place.address
    if has_existing_real_address:
        if addresses_match(old_address, candidate):
            if apply:
                _mark_existing_address_verified(db, place)
            stats["verified_existing"] += 1
            _append_result(stats, place, "verified_existing", old_address=old_address, new_address=candidate)
        else:
            if apply:
                _mark_address_for_review(db, place, candidate)
            stats["sent_to_review"] += 1
            _append_result(stats, place, "sent_to_review", old_address=old_address, new_address=candidate)
        time.sleep(sleep_seconds)
        return

    if apply:
        place.address = candidate
        place.address_source = "nominatim"
        place.address_confidence = 0.75
        place.address_updated_at = datetime.utcnow()
        place.updated_at = datetime.utcnow()
        db.add(place)
        db.commit()
        db.expunge(place)
        stats["updated"] += 1
    else:
        stats["updated"] += 1

    _append_result(stats, place, "updated" if apply else "dry_run", old_address=old_address, new_address=candidate)
    time.sleep(sleep_seconds)


def addresses_match(current: str | None, candidate: str | None) -> bool:
    current_tokens = _address_tokens(current)
    candidate_tokens = _address_tokens(candidate)
    if not current_tokens or not candidate_tokens:
        return False
    score = len(current_tokens & candidate_tokens) / max(len(current_tokens), len(candidate_tokens))
    if score >= ADDRESS_MATCH_THRESHOLD:
        return True
    current_digits = _digits(current)
    candidate_digits = _digits(candidate)
    return bool(current_digits and candidate_digits and current_digits == candidate_digits and (current_tokens & candidate_tokens))


def _address_tokens(value: str | None) -> set[str]:
    normalized = str(value or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[,.()\[\]{}:;№#]", " ", normalized)
    stop_words = {"город", "ул", "улица", "пр", "проспект", "пер", "переулок", "дом", "район", "область"}
    return {token for token in re.split(r"\s+", normalized) if token and len(token) > 1 and token not in stop_words}


def _digits(value: str | None) -> set[str]:
    return set(re.findall(r"\d+[а-яa-z]?", str(value or "").casefold()))


def _mark_existing_address_verified(db: Session, place: Place) -> None:
    place.address_source = place.address_source or "nominatim_verified"
    place.address_confidence = max(float(place.address_confidence or 0), 0.75)
    place.address_updated_at = datetime.utcnow()
    place.updated_at = datetime.utcnow()
    db.add(place)
    db.commit()
    db.expunge(place)


def _mark_address_for_review(db: Session, place: Place, candidate: str) -> None:
    place.verification_status = "needs_recheck"
    place.verification_source = "nominatim"
    place.verification_method = "address_conflict"
    place.verification_comment = (
        f"Address conflict. Current: {place.address or ''}. Candidate: {candidate or ''}."
    )[:1000]
    place.needs_recheck_at = datetime.utcnow()
    place.updated_at = datetime.utcnow()
    db.add(place)
    db.commit()
    db.expunge(place)


def _clear_placeholder(db: Session, place: Place, stats: dict[str, Any]) -> None:
    if is_real_address(place.address):
        return
    place.address = ""
    place.updated_at = datetime.utcnow()
    db.add(place)
    db.commit()
    stats["cleared_placeholders"] += 1


def _append_result(stats: dict[str, Any], place: Place, status: str, **extra: object) -> None:
    if stats.get("mode") == "apply":
        return
    results = stats["results"]
    if not isinstance(results, list):
        return
    results.append({"place_id": place.id, "title": place.title, "status": status, **extra})
