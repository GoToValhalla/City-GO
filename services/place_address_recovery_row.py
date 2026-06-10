"""Оценка одной строки review CSV (preview/apply)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from models.place import Place
from services.place_address_policy import is_replaceable_address
from services.place_address_recovery_assess import assess_proposed_address

RowOutcome = Literal[
    "would_apply",
    "applied",
    "skipped_should_apply_false",
    "skipped_empty_proposed",
    "skipped_policy",
    "skipped_missing_place",
    "skipped_existing_real_address",
    "error",
]


def evaluate_review_row(db: Session, row: dict[str, str]) -> tuple[RowOutcome, str, Place | None]:
    if not _truthy(row.get("should_apply")):
        return "skipped_should_apply_false", "should_apply_false", None
    proposed = str(row.get("proposed_address") or "").strip()
    if not proposed:
        return "skipped_empty_proposed", "empty_proposed", None
    assessment = assess_proposed_address(proposed, row.get("category"))
    if not assessment.get("should_apply"):
        return "skipped_policy", str(assessment.get("skip_reason") or "policy"), None
    place = _find_place(db, row)
    if place is None:
        return "skipped_missing_place", "missing_place", None
    if not is_replaceable_address(place.address, place.category):
        return "skipped_existing_real_address", "existing_real_address", place
    return "would_apply", proposed, place


def _find_place(db: Session, row: dict[str, str]) -> Place | None:
    place_id = str(row.get("place_id") or "").strip()
    if place_id.isdigit():
        found = db.query(Place).filter(Place.id == int(place_id)).first()
        if found:
            return found
    slug = str(row.get("slug") or "").strip()
    return db.query(Place).filter(Place.slug == slug).first() if slug else None


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "yes", "да"}


def sample(stats: dict[str, Any], bucket: str, row: dict[str, str], detail: str) -> None:
    samples = stats["samples"][bucket]
    if len(samples) >= 10:
        return
    samples.append({"place_id": row.get("place_id"), "title": row.get("title"), "detail": detail})
