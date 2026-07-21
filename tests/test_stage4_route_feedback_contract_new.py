from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.route_feedback import RouteFeedbackCreate


ROOT = Path(__file__).resolve().parents[1]
ROUTER_SOURCE = (ROOT / "routers" / "route_feedback.py").read_text(encoding="utf-8")


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


def test_route_feedback_router_reuses_existing_user_signal_for_duplicate_new() -> None:
    assert "_DUPLICATE_WINDOW = timedelta(minutes=5)" in ROUTER_SOURCE
    assert "latest.payload == signal_payload" in ROUTER_SOURCE
    assert "return RouteFeedbackRead.model_validate(latest)" in ROUTER_SOURCE
    assert ROUTER_SOURCE.index("return RouteFeedbackRead.model_validate(latest)") < ROUTER_SOURCE.index("signal = UserSignal(")


def test_public_feedback_payload_excludes_technical_diagnostics_new() -> None:
    assert '"rating": payload.rating' in ROUTER_SOURCE
    assert '"problem_types": payload.problem_types' in ROUTER_SOURCE
    assert "route_payload" not in ROUTER_SOURCE
    assert "debug_trace" not in ROUTER_SOURCE
    assert "stack" not in ROUTER_SOURCE.lower()
