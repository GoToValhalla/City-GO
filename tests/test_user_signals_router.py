from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from models.user_signal import UserSignal
from schemas.user_signal import UserDerivedProfile, UserSignalSummary

_ANON_HEADERS = {"X-Anonymous-Session": "test-anonymous-session-token"}


def test_user_signal_summary_endpoint_returns_counts() -> None:
    summary = UserSignalSummary(
        user_id="u1",
        total=1,
        by_signal_type={"view_place": 1},
        by_entity_type={"place": 1},
    )
    with patch("routers.user_signals.summarize_user_signals", return_value=summary):
        response = TestClient(app).get("/user-signals/summary", headers=_ANON_HEADERS)
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_user_signal_create_endpoint_returns_signal() -> None:
    signal = MagicMock()
    signal.id = 1
    signal.user_id = "u1"
    signal.signal_type = "view_place"
    signal.entity_type = "place"
    signal.entity_id = "p1"
    signal.payload = None
    signal.created_at = datetime(2030, 1, 1)
    with patch("routers.user_signals.create_user_signal", return_value=signal):
        response = TestClient(app).post(
            "/user-signals/",
            headers=_ANON_HEADERS,
            json={"user_id": "spoofed", "signal_type": "view_place", "entity_type": "place", "entity_id": "p1"},
        )
    assert response.status_code == 200
    assert response.json()["signal_type"] == "view_place"


def test_generic_endpoint_rejects_reserved_route_feedback_signal_type_new(client, db_session) -> None:
    """The confirmed bypass: /user-signals/ must never be able to create a
    route_feedback-typed row -- that type is owned exclusively by the
    dedicated /route-feedback/ endpoint, which enforces rating/payload
    validation and atomic deduplication this generic path does not."""
    response = client.post(
        "/user-signals/",
        headers=_ANON_HEADERS,
        json={"signal_type": "route_feedback", "entity_type": "route", "entity_id": "route-1", "payload": {"rating": 5}},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "RESERVED_SIGNAL_TYPE"
    assert db_session.query(UserSignal).filter(UserSignal.entity_id == "route-1").count() == 0


def test_generic_endpoint_rejects_reserved_type_for_an_authenticated_caller_too_new(client, db_session) -> None:
    """The rejection must not depend on anonymous vs. identified caller --
    a real user_id in the payload must not unlock the bypass either."""
    response = client.post(
        "/user-signals/",
        json={"user_id": "real-user-42", "signal_type": "route_feedback", "entity_type": "route", "entity_id": "route-2", "payload": {"rating": 1}},
    )

    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "RESERVED_SIGNAL_TYPE"
    assert db_session.query(UserSignal).filter(UserSignal.entity_id == "route-2").count() == 0


def test_generic_endpoint_rejects_case_and_whitespace_variants_of_the_reserved_type_new(client, db_session) -> None:
    """Case/whitespace must not become a bypass vector for the reserved-type
    check -- "Route_Feedback", padded, or upper-cased variants must all be
    rejected exactly like the canonical literal."""
    for variant in ("Route_Feedback", " route_feedback ", "ROUTE_FEEDBACK", "RoUtE_fEeDbAcK"):
        response = client.post(
            "/user-signals/",
            headers=_ANON_HEADERS,
            json={"signal_type": variant, "entity_type": "route", "entity_id": f"route-variant-{variant}", "payload": {"rating": 5}},
        )
        assert response.status_code == 409, (variant, response.text)
        assert response.json()["detail"]["code"] == "RESERVED_SIGNAL_TYPE"

    assert db_session.query(UserSignal).filter(UserSignal.entity_type == "route").count() == 0


def test_generic_endpoint_rejects_repeated_crafted_requests_for_the_reserved_type_new(client, db_session) -> None:
    """Repeated attempts must not eventually succeed, accumulate partial
    state, or degrade into a different code path -- every crafted request
    is rejected deterministically and independently."""
    for _ in range(5):
        response = client.post(
            "/user-signals/",
            headers=_ANON_HEADERS,
            json={"signal_type": "route_feedback", "entity_type": "route", "entity_id": "route-repeat", "payload": {"rating": 3}},
        )
        assert response.status_code == 409

    assert db_session.query(UserSignal).filter(UserSignal.entity_id == "route-repeat").count() == 0


def test_generic_endpoint_still_accepts_legitimate_non_reserved_signal_types_new(client, db_session) -> None:
    """The fix must not break any legitimate existing generic signal flow --
    only the reserved type is blocked."""
    response = client.post(
        "/user-signals/",
        headers=_ANON_HEADERS,
        json={"signal_type": "favorite_place", "entity_type": "place", "entity_id": "place-1"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["signal_type"] == "favorite_place"
    signal = db_session.query(UserSignal).filter(UserSignal.entity_id == "place-1").one()
    assert signal.signal_type == "favorite_place"
    assert signal.dedup_key is None


def test_dedicated_route_feedback_endpoint_still_deduplicates_atomically_after_the_fix_new(client, db_session) -> None:
    """The dedicated endpoint's own atomic dedup guarantee must be
    unaffected by the generic endpoint's new rejection -- a real repeated
    submission through /route-feedback/ must still collapse into one row."""
    payload = {"route_id": "route-dedup-check", "rating": 4, "user_id": "stable-user-check"}
    first = client.post("/route-feedback/", json=payload)
    second = client.post("/route-feedback/", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]
    rows = db_session.query(UserSignal).filter(UserSignal.entity_id == "route-dedup-check").all()
    assert len(rows) == 1


def test_admin_route_feedback_read_cannot_surface_rows_from_the_generic_endpoint_new(client, db_session) -> None:
    """Even if the reserved-type rejection were ever bypassed by some other
    write path, the admin read must only ever see rows actually inserted
    through the dedicated endpoint. This proves the read side is honest
    about its source: a legitimate feedback submission appears, and no
    row can be manufactured through the generic endpoint to appear
    alongside it (the rejected request above never persisted a route
    row at all)."""
    client.post("/route-feedback/", json={"route_id": "route-admin-check", "rating": 5, "user_id": "admin-check-user"})
    rejected = client.post(
        "/user-signals/",
        headers=_ANON_HEADERS,
        json={"signal_type": "route_feedback", "entity_type": "route", "entity_id": "route-admin-check-bypass", "payload": {"rating": 5}},
    )
    assert rejected.status_code == 409

    response = client.get("/admin/route-feedback")
    assert response.status_code == 200, response.text
    route_ids = {item["route_id"] for item in response.json()["items"]}
    assert "route-admin-check" in route_ids
    assert "route-admin-check-bypass" not in route_ids


def test_user_derived_profile_endpoint_returns_profile() -> None:
    profile = UserDerivedProfile(
        user_id="u1",
        total_signals=1,
        preferred_categories={"coffee": 1},
        action_counts={"view_place": 1},
    )
    with patch("routers.user_signals.derive_user_profile", return_value=profile):
        response = TestClient(app).get("/user-signals/profile", headers=_ANON_HEADERS)
    assert response.status_code == 200
    assert response.json()["preferred_categories"] == {"coffee": 1}
