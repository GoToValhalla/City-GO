"""CITYGO-315: deterministic import accounting validation.

Proves:
    requested == accepted + failed + rejected
and
    accepted == created + updated + unchanged + hidden + sent_to_review

matched_existing is deliberately excluded from the second equation — see
services/import_funnel_validation.py's module docstring for why (it is an
orthogonal flag, not a distinct terminal bucket; CITYGO-313's own tests
already show an item can be both matched_existing=1 and sent_to_review=1).

No silent correction: validate_funnel_accounting never mutates its input
and never guesses a missing value — "unavailable" fields make the result
unchecked (checked=False), not a fabricated pass or fail.
"""

from __future__ import annotations

from typing import Any

from data.scripts.import_city_osm import _apply_import, _normalize_osm_object
from models.city import City
from models.city_import_scope import CityImportScope
from services.admin_city_import_runner import summarize_import_results
from services.import_funnel_validation import validate_funnel_accounting


def _funnel(**overrides: object) -> dict[str, object]:
    base = {
        "requested": 10,
        "fetched": 10,
        "deduplicated": "unavailable",
        "normalized": 10,
        "accepted": 7,
        "rejected_by_reason": {"missing_name": 2, "hidden_category": 1},
        "matched_existing": 2,
        "created": 3,
        "updated": 1,
        "unchanged": 1,
        "hidden": 0,
        "sent_to_review": 2,
        "failed": 0,
    }
    base.update(overrides)
    return base


def test_accounting_passes_for_consistent_funnel_new():
    result = validate_funnel_accounting(_funnel())

    assert result.checked is True
    assert result.ok is True
    assert result.reason is None
    assert result.requested_equation["sum"] == 10
    assert result.accepted_equation["sum"] == 7


def test_accounting_fails_loudly_on_requested_mismatch_new():
    """accepted + failed + rejected must equal requested exactly — a
    mismatch is reported with the exact numbers, not silently corrected."""
    result = validate_funnel_accounting(_funnel(requested=11))

    assert result.checked is True
    assert result.ok is False
    assert result.reason == "accounting_mismatch"
    assert result.requested_equation["ok"] is False
    assert result.requested_equation["requested"] == 11
    assert result.requested_equation["sum"] == 10


def test_accounting_fails_loudly_on_accepted_mismatch_new():
    result = validate_funnel_accounting(_funnel(accepted=8))

    assert result.checked is True
    assert result.ok is False
    assert result.accepted_equation["ok"] is False
    assert result.accepted_equation["accepted"] == 8
    assert result.accepted_equation["sum"] == 7


def test_accounting_excludes_matched_existing_from_accepted_sum_new():
    """A matched-existing item that is ALSO sent_to_review must not be
    double-counted — matched_existing is informational, not a sixth
    terminal bucket. This funnel has matched_existing=5 (more than
    sent_to_review itself) and must still pass, proving the equation does
    not include it."""
    result = validate_funnel_accounting(_funnel(matched_existing=5))

    assert result.checked is True
    assert result.ok is True


def test_accounting_derives_rejected_from_rejected_by_reason_not_a_separate_field_new():
    """rejected is computed as sum(rejected_by_reason.values()) — the exact
    figures the pipeline already recorded per reason — never read from a
    separately-reported total that could drift out of sync."""
    funnel = _funnel(rejected_by_reason={"missing_name": 1, "missing_coordinates": 2}, requested=10, accepted=7, failed=0)
    # sum(rejected_by_reason) = 3, so requested must be accepted+failed+3 = 10 to pass
    result = validate_funnel_accounting(funnel)

    assert result.checked is True
    assert result.ok is True
    assert result.requested_equation["rejected"] == 3


def test_accounting_unchecked_when_funnel_missing_new():
    """None (funnel never produced) is a genuinely different fact from a
    verified-consistent or verified-inconsistent funnel — checked=False,
    never a fabricated ok=True."""
    result = validate_funnel_accounting(None)

    assert result.checked is False
    assert result.ok is False
    assert result.reason == "funnel_missing"


def test_accounting_unchecked_when_any_required_field_is_unavailable_new():
    """"unavailable" must never be treated as 0 — the equation cannot be
    verified at all when a required field wasn't actually computed."""
    result = validate_funnel_accounting(_funnel(requested="unavailable"))

    assert result.checked is False
    assert result.ok is False
    assert result.reason is not None
    assert "requested" in result.reason


def test_accounting_unchecked_when_all_scopes_failed_new():
    """Companion to CITYGO-313's "every scope failed -> funnel is entirely
    'unavailable'" behavior: the validator must not report a fabricated
    all-zero pass for a funnel that never actually ran."""
    unavailable_funnel = {
        "requested": "unavailable", "fetched": "unavailable", "deduplicated": "unavailable",
        "normalized": "unavailable", "accepted": "unavailable", "rejected_by_reason": {},
        "matched_existing": "unavailable", "created": "unavailable", "updated": "unavailable",
        "unchanged": "unavailable", "hidden": "unavailable", "sent_to_review": "unavailable",
        "failed": "unavailable",
    }
    result = validate_funnel_accounting(unavailable_funnel)

    assert result.checked is False
    assert result.ok is False


def test_accounting_unchecked_when_rejected_by_reason_value_is_unavailable_new():
    result = validate_funnel_accounting(_funnel(rejected_by_reason={"missing_name": "unavailable"}))

    assert result.checked is False
    assert result.ok is False
    assert result.reason == "rejected_by_reason_value_unavailable"


def test_accounting_does_not_mutate_input_funnel_new():
    funnel = _funnel()
    original = dict(funnel)

    validate_funnel_accounting(funnel)

    assert funnel == original


def test_accounting_handles_zero_requested_as_a_real_pass_not_unavailable_new():
    """A scope that genuinely found nothing (requested=0, accepted=0,
    failed=0, rejected=0) is a legitimate, checked, consistent result — not
    an unavailable one."""
    empty_funnel = _funnel(
        requested=0, fetched=0, normalized=0, accepted=0, rejected_by_reason={},
        matched_existing=0, created=0, updated=0, unchanged=0, hidden=0, sent_to_review=0, failed=0,
    )
    result = validate_funnel_accounting(empty_funnel)

    assert result.checked is True
    assert result.ok is True


# --- integration: the REAL funnel produced by _apply_import must itself
# pass this validator, proving the two independently-built pieces
# (CITYGO-313's funnel construction and CITYGO-315's validator) actually
# agree on the same accounting, not just in hand-written fixtures. ---


def _city_and_scope(db_session, slug: str) -> tuple[City, CityImportScope]:
    city = City(slug=slug, name="Accounting City", country="Test")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    return city, scope


def _node(osm_id: int, *, name: str = "Кафе", amenity: str = "cafe", lat: float = 54.9, lng: float = 20.5) -> dict[str, Any]:
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lng, "tags": {"name": name, "amenity": amenity}}


def test_real_apply_import_funnel_passes_accounting_validation_new(db_session):
    city, scope = _city_and_scope(db_session, "accounting-real-pipeline")
    raw = [
        _node(1, name="Кафе Раз"),
        _node(2, name=""),  # rejected: missing_name
        _node(3, amenity="atm"),  # rejected: hidden_category
        {"type": "node", "id": 4, "tags": {"name": "Плохо", "amenity": "cafe"}},  # rejected: missing_coordinates
    ]
    normalized = [_normalize_osm_object(item, city.slug) for item in raw]

    result = _apply_import(db_session, city, scope, "tourist_core", raw, normalized)

    accounting = validate_funnel_accounting(result["funnel"])
    assert accounting.checked is True
    assert accounting.ok is True


def test_real_summarize_import_results_funnel_passes_accounting_validation_new(db_session):
    """Same proof, one level up: the cross-scope aggregate funnel produced
    by summarize_import_results (CITYGO-313's found=136/saved=0 fix) must
    also satisfy the accounting equations, not just a single scope's raw
    funnel."""
    city_a, scope_a = _city_and_scope(db_session, "accounting-real-scope-a")
    city_b, scope_b = _city_and_scope(db_session, "accounting-real-scope-b")
    raw_a = [_node(1, name="Кафе Раз"), _node(2, name="")]
    raw_b = [_node(3, name="Кафе Три"), _node(4, amenity="atm")]

    result_a = _apply_import(db_session, city_a, scope_a, "tourist_core", raw_a, [_normalize_osm_object(i, city_a.slug) for i in raw_a])
    result_b = _apply_import(db_session, city_b, scope_b, "tourist_core", raw_b, [_normalize_osm_object(i, city_b.slug) for i in raw_b])

    payload = {"results": [
        {"status": "success", "scope": "a", "import_result": result_a},
        {"status": "success", "scope": "b", "import_result": result_b},
    ]}
    summary = summarize_import_results(payload)

    accounting = validate_funnel_accounting(summary["funnel"])
    assert accounting.checked is True
    assert accounting.ok is True
