"""CITYGO-315: deterministic import accounting validation.

Proves, from an already-produced funnel dict (never a second computation
of import data), that:

    requested == accepted + failed + rejected

and

    accepted == created + updated + unchanged + hidden + sent_to_review

`matched_existing` is deliberately excluded from the second equation: it is
an orthogonal flag on an item (a matched place can simultaneously be
`sent_to_review`, `updated`, etc.), not a distinct terminal bucket in the
funnel's own partition — CITYGO-313's tests already establish an item can be
both matched_existing=1 and sent_to_review=1 at once, so including it in the
sum would double-count and make this validator permanently fail on correct
data.

`rejected` is derived here as `sum(rejected_by_reason.values())` — the exact
figure the pipeline already recorded per rejection, never re-derived from a
different source (see data/scripts/import_city_osm.py's rejection_reasons
Counter, which this validator reads back verbatim through the funnel).

This module never mutates a funnel, a job, or any import/publication state.
It only reports whether the numbers a completed run already produced are
internally consistent — for a diagnostics/observability purpose (CITYGO-316
exposes its output), not to gate or alter import execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_UNAVAILABLE = "unavailable"

_REQUESTED_EQUATION_FIELDS = ("requested", "accepted", "failed", "rejected")
_ACCEPTED_EQUATION_FIELDS = ("accepted", "created", "updated", "unchanged", "hidden", "sent_to_review")


@dataclass(frozen=True)
class FunnelAccountingResult:
    ok: bool
    checked: bool
    reason: str | None = None
    requested_equation: dict[str, object] = field(default_factory=dict)
    accepted_equation: dict[str, object] = field(default_factory=dict)


def _is_unavailable(value: object) -> bool:
    return value == _UNAVAILABLE


def _as_int_or_none(value: object) -> int | None:
    if _is_unavailable(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def validate_funnel_accounting(funnel: dict[str, object] | None) -> FunnelAccountingResult:
    """Fails loudly (ok=False, with the exact mismatching numbers) rather
    than silently correcting anything. Returns checked=False — not ok=True —
    when the funnel itself is unavailable/missing/partial, since "no data to
    check" is a different fact from "checked and consistent"."""
    if not isinstance(funnel, dict):
        return FunnelAccountingResult(ok=False, checked=False, reason="funnel_missing")

    rejected_by_reason = funnel.get("rejected_by_reason")
    if not isinstance(rejected_by_reason, dict):
        return FunnelAccountingResult(ok=False, checked=False, reason="rejected_by_reason_missing")
    rejected_total = 0
    for reason_count in rejected_by_reason.values():
        count = _as_int_or_none(reason_count)
        if count is None:
            return FunnelAccountingResult(ok=False, checked=False, reason="rejected_by_reason_value_unavailable")
        rejected_total += count

    values: dict[str, int | None] = {}
    for field_name in set(_REQUESTED_EQUATION_FIELDS) | set(_ACCEPTED_EQUATION_FIELDS):
        raw = funnel.get(field_name)
        values[field_name] = _as_int_or_none(raw)
    values["rejected"] = rejected_total

    unavailable_fields = [name for name in _REQUESTED_EQUATION_FIELDS + _ACCEPTED_EQUATION_FIELDS if values.get(name) is None]
    if unavailable_fields:
        return FunnelAccountingResult(
            ok=False,
            checked=False,
            reason=f"unavailable_fields:{','.join(sorted(set(unavailable_fields)))}",
        )

    requested = values["requested"] or 0
    accepted = values["accepted"] or 0
    failed = values["failed"] or 0
    rejected = values["rejected"] or 0
    requested_sum = accepted + failed + rejected
    requested_ok = requested == requested_sum

    created = values["created"] or 0
    updated = values["updated"] or 0
    unchanged = values["unchanged"] or 0
    hidden = values["hidden"] or 0
    sent_to_review = values["sent_to_review"] or 0
    accepted_sum = created + updated + unchanged + hidden + sent_to_review
    accepted_ok = accepted == accepted_sum

    return FunnelAccountingResult(
        ok=requested_ok and accepted_ok,
        checked=True,
        reason=None if (requested_ok and accepted_ok) else "accounting_mismatch",
        requested_equation={
            "requested": requested,
            "accepted": accepted,
            "failed": failed,
            "rejected": rejected,
            "sum": requested_sum,
            "ok": requested_ok,
        },
        accepted_equation={
            "accepted": accepted,
            "created": created,
            "updated": updated,
            "unchanged": unchanged,
            "hidden": hidden,
            "sent_to_review": sent_to_review,
            "sum": accepted_sum,
            "ok": accepted_ok,
        },
    )
