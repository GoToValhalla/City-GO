from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_admin_backlog_breakdown_new import FORBIDDEN_COPY, _make_place


def test_backlog_reduction_plan_returns_safe_operator_actions_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "plan-service", category="bank", canonical_category="bank")
    response = client.get("/admin/overview/backlog-reduction-plan")

    assert response.status_code == 200
    payload = response.json()
    action_codes = {action["code"] for action in payload["actions"]}

    assert "recompute_route_eligibility" in action_codes
    assert "exclude_service_places_from_routes" in action_codes
    assert "classify_unknown_categories_deterministic" in action_codes
    assert "normalize_manual_review_backlog" in action_codes
    assert payload["summary"]["route_blockers_reducible"] >= 1
    assert all(action["requires_confirmation"] is True for action in payload["actions"])
    assert all(action["risk_level"] == "safe" for action in payload["actions"])


def test_backlog_breakdown_links_reduction_plan_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "breakdown-action", image_url=None)
    response = client.get("/admin/overview/backlog-breakdown")

    assert response.status_code == 200
    payload = response.json()

    assert payload["reduction_available"] is True
    assert payload["reduction_plan_endpoint"] == "/admin/overview/backlog-reduction-plan"
    assert payload["top_actions"]
    assert payload["last_reduction_result"] is None


def test_reduction_plan_copy_is_operator_readable_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "copy-guard", publication_status="needs_review", is_published=False, is_visible_in_catalog=False)
    payload = client.get("/admin/overview/backlog-reduction-plan").json()

    visible_text = " ".join(
        " ".join(str(action[key]) for key in ("title", "description", "expected_effect"))
        for action in payload["actions"]
    ).casefold()

    for term in FORBIDDEN_COPY:
        assert term not in visible_text, term


def test_disabled_reduction_action_is_explained_new(client: TestClient) -> None:
    payload = client.get("/admin/overview/backlog-reduction-plan").json()
    action = next(item for item in payload["actions"] if item["code"] == "recompute_low_confidence")

    assert action["enabled"] is False
    assert action["disabled_reason"]
    assert action["affected_count"] == 0
