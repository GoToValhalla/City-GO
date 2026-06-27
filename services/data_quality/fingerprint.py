"""Stable fingerprints for idempotent data quality rows."""

from hashlib import sha256


def issue_fingerprint(
    *,
    place_id: int | None,
    city_id: int | None,
    issue_type: str,
    reason: str,
    source: str,
) -> str:
    parts = (place_id or "city", city_id or "global", issue_type, reason, source)
    return sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def candidate_fingerprint(*, issue_id: int, candidate_type: str, patch: dict[str, object]) -> str:
    patch_key = "|".join(f"{key}={patch[key]}" for key in sorted(patch))
    return sha256(f"{issue_id}|{candidate_type}|{patch_key}".encode("utf-8")).hexdigest()
