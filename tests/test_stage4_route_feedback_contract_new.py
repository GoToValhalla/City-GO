from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.route_feedback import RouteFeedbackCreate


ROOT = Path(__file__).resolve().parents[1]
ROUTER_SOURCE = (ROOT / "routers" / "route_feedback.py").read_text(encoding="utf-8")
USER_SIGNALS_ROUTER_SOURCE = (ROOT / "routers" / "user_signals.py").read_text(encoding="utf-8")


def test_route_feedback_normalizes_public_input_new() -> None:
    payload = RouteFeedbackCreate(
        route_id="  route-1  ",
        rating=2,
        comment="  Не подходит  ",
        source="TMA",
        problem_types=["bad_route", "bad_route", "too_long"],
    )

    assert payload.route_id == "route-1"
    assert payload.comment == "Не подходит"
    assert payload.source == "telegram"
    assert payload.problem_types == ["bad_route", "too_long"]


def test_route_feedback_rejects_internal_or_unknown_categories_new() -> None:
    with pytest.raises(ValidationError):
        RouteFeedbackCreate(
            route_id="route-1",
            rating=1,
            source="admin-debug",
            problem_types=["provider_stack_trace"],
        )


def test_route_feedback_router_deduplicates_atomically_at_the_database_level_new() -> None:
    """Static contract, paired with the real-database behavioral proof in
    tests/test_route_feedback_new.py: deduplication must be an atomic
    INSERT ... ON CONFLICT DO NOTHING against a unique-indexed column,
    never a check-then-insert read followed by a separate write (which
    cannot close a race between two concurrent requests)."""
    assert "_DUPLICATE_WINDOW = timedelta(minutes=5)" in ROUTER_SOURCE
    assert "on_conflict_do_nothing" in ROUTER_SOURCE
    assert "dedup_key" in ROUTER_SOURCE
    # The exact defect being guarded against: a bare read (SELECT ... latest)
    # followed by a conditional, non-atomic decision to insert.
    assert "latest.payload == signal_payload" not in ROUTER_SOURCE


def test_route_feedback_router_never_collapses_anonymous_identity_into_a_shared_constant_new() -> None:
    """Static contract for defect #9: the router must never fall back to
    a single shared literal identity for every caller lacking a real
    identity -- see the real behavioral proof (two independent anonymous
    callers get independent rows) in tests/test_route_feedback_new.py."""
    assert 'anonymous_subject or "anonymous"' not in ROUTER_SOURCE
    assert "_dedup_subject" in ROUTER_SOURCE


def test_route_feedback_signal_type_is_the_single_shared_authoritative_constant_new() -> None:
    """Static contract: the dedicated endpoint's signal type must come from
    the one shared reserved-type registry (schemas/user_signal.py), not a
    locally re-declared string literal -- otherwise the generic endpoint's
    rejection list and the dedicated endpoint's own signal_type could
    silently drift apart."""
    assert "from schemas.user_signal import SIGNAL_ROUTE_FEEDBACK" in ROUTER_SOURCE
    assert '_SIGNAL_TYPE = SIGNAL_ROUTE_FEEDBACK' in ROUTER_SOURCE


def test_generic_user_signals_endpoint_rejects_the_reserved_route_feedback_type_new() -> None:
    """Static contract, paired with the real-behavior proof in
    tests/test_user_signals_router.py: the generic ingestion endpoint must
    reject the reserved type using the shared registry, never a duplicated
    validation/dedup implementation and never a silent internal proxy to
    the dedicated endpoint (whose schema it cannot satisfy)."""
    assert "RESERVED_SIGNAL_TYPES" in USER_SIGNALS_ROUTER_SOURCE
    assert "on_conflict_do_nothing" not in USER_SIGNALS_ROUTER_SOURCE
    assert "dedup_key" not in USER_SIGNALS_ROUTER_SOURCE
    # Naming the dedicated endpoint in a comment is fine; actually calling
    # out to it (an internal proxy/redirect) is the thing that must never
    # happen, since the generic schema cannot satisfy its contract.
    assert "requests.post" not in USER_SIGNALS_ROUTER_SOURCE
    assert "httpx" not in USER_SIGNALS_ROUTER_SOURCE
    assert "RedirectResponse" not in USER_SIGNALS_ROUTER_SOURCE
    assert "post_route_feedback(" not in USER_SIGNALS_ROUTER_SOURCE


def test_public_feedback_payload_excludes_technical_diagnostics_new() -> None:
    assert '"rating": payload.rating' in ROUTER_SOURCE
    assert '"problem_types": payload.problem_types' in ROUTER_SOURCE
    assert "route_payload" not in ROUTER_SOURCE
    assert "debug_trace" not in ROUTER_SOURCE
    assert "stack" not in ROUTER_SOURCE.lower()
